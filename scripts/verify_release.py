#!/usr/bin/env python3
"""Read-only release gate: prevent serving mixed frontend/backend revisions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.request import Request, urlopen


def check_release(release, public_url, service, nginx_site):
    release = Path(release).resolve()
    revision = subprocess.check_output(['git', '-C', str(release), 'rev-parse', 'HEAD'], text=True).strip()
    cwd = subprocess.check_output(['systemctl', '--user', 'show', service, '-p', 'WorkingDirectory', '--value'], text=True).strip()
    if Path(cwd).resolve() != release:
        raise ValueError('Backend WorkingDirectory does not match requested release')
    pid = subprocess.check_output(['systemctl', '--user', 'show', service, '-p', 'MainPID', '--value'], text=True).strip()
    if Path('/proc', pid, 'cwd').resolve() != release:
        raise ValueError('Running backend cwd does not match release (restart missing)')
    roots = re.findall(r'^\s*root\s+([^;]+);', Path(nginx_site).read_text(), re.M)
    expected_dist = release / 'web/frontend/dist'
    # A named fallback location may serve old hashed assets to already-open tabs.
    # The primary asset and SPA roots must both be current.
    if len(roots) < 2 or any(Path(root).resolve() != expected_dist for root in roots[:2]):
        raise ValueError('Primary Nginx frontend roots do not match backend release')
    def get(path):
        request = Request(public_url.rstrip('/') + path, headers={'User-Agent': 'Mozilla/5.0 TranslationReleaseCheck/1.0'})
        with urlopen(request, timeout=30) as response:
            return response.read()
    manifest = json.loads(get('/release.json'))
    if manifest['revision'] != revision:
        raise ValueError('Public release manifest does not match git revision')
    index = get('/')
    local_index = (expected_dist / 'index.html').read_bytes()
    # Cloudflare may inject its analytics beacon for browser-like user agents.
    # Remove only that known external tag; preserve all app markup and references.
    def normalized_html(value):
        text = value.decode()
        text = re.sub(r'<script\b[^>]*\bsrc="https://static\.cloudflareinsights\.com/beacon\.min\.js[^"\s]*"[^>]*>\s*</script>', '', text)
        return re.sub(r'>\s+<', '><', text).strip()
    if normalized_html(index) != normalized_html(local_index):
        raise ValueError('Public entry HTML does not match release build')
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', index.decode())
    if not assets:
        raise ValueError('No frontend entry assets found')
    for asset in assets:
        if hashlib.sha256(get(asset)).digest() != hashlib.sha256((expected_dist / asset.lstrip('/')).read_bytes()).digest():
            raise ValueError('Public asset mismatch: ' + asset)
    public_identity = json.loads(get('/api/release'))
    request = Request('http://127.0.0.1:54321/api/release')
    with urlopen(request, timeout=10) as response:
        local_identity = json.load(response)
    if (public_identity.get('revision') != revision
            or not public_identity.get('instance_id')
            or public_identity != local_identity):
        raise ValueError('Public/local backend process identity does not match release')
    health = json.loads(get('/api/health'))
    if health.get('status') != 'healthy':
        raise ValueError('Backend health check failed')
    return {'revision': revision, 'release': str(release), 'public_url': public_url,
            'entry_assets_verified': len(assets), 'backend_frontend_aligned': True, 'health': 'healthy'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True)
    parser.add_argument('--public-url', default='https://momo.beauty')
    parser.add_argument('--service', default='translation-agent-live.service')
    parser.add_argument('--nginx-site', default='/etc/nginx/sites-enabled/translation-agent')
    args = parser.parse_args()
    print(json.dumps(check_release(args.release, args.public_url, args.service, args.nginx_site), indent=2))
