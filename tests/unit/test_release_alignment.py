import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('verify_release', Path(__file__).resolve().parents[2] / 'scripts/verify_release.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def test_mixed_backend_is_rejected(tmp_path):
    with patch.object(verify.subprocess, 'check_output', side_effect=['abc\n', '/wrong/backend\n']):
        try:
            verify.check_release(tmp_path, 'https://example.test', 'app', tmp_path / 'nginx')
        except ValueError as exc:
            assert 'WorkingDirectory' in str(exc)
        else:
            raise AssertionError('mixed backend accepted')


def test_matching_release_and_assets(tmp_path):
    dist = tmp_path / 'web/frontend/dist'
    (dist / 'assets').mkdir(parents=True)
    html = b'<script src="/assets/app-123.js"></script>'
    (dist / 'index.html').write_bytes(html)
    (dist / 'assets/app-123.js').write_bytes(b'console.log(1)')
    nginx = tmp_path / 'nginx.conf'
    nginx.write_text(f'root {dist};\nroot {dist};\nroot /old/fallback;\n')
    responses = {'/': html, '/release.json': b'{"revision":"abc"}', '/api/health': b'{"status":"healthy"}', '/assets/app-123.js': b'console.log(1)'}
    import io
    original_resolve = Path.resolve
    def resolve(path, *args, **kwargs):
        if str(path) == '/proc/123/cwd':
            return tmp_path
        return original_resolve(path, *args, **kwargs)
    with patch.object(verify.subprocess, 'check_output', side_effect=['abc\n', str(tmp_path), '123']), patch.object(Path, 'resolve', resolve), patch.object(verify, 'urlopen', side_effect=lambda url, **kwargs: io.BytesIO(responses[url.removeprefix('https://example.test')])):
        result = verify.check_release(tmp_path, 'https://example.test', 'app', nginx)
    assert result['backend_frontend_aligned'] is True
    assert result['entry_assets_verified'] == 1
