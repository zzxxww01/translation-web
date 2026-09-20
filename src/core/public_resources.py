"""Bounded public HTTP fetches and confined local resources for untrusted documents.

Every redirect is validated. Connections use the already checked numeric address,
not a second DNS lookup, while HTTPS verifies the original hostname. These fetches
never inherit proxy settings or credentials from the model-provider transport.
"""
from __future__ import annotations

from contextlib import contextmanager
import http.client
import io
import ipaddress
import os
from pathlib import Path
import socket
import ssl
import tempfile
import time
from urllib.parse import quote, unquote, urljoin, urlsplit

from .url_safety import is_safe_ip, is_safe_url

MAX_RESOURCE_BYTES = 20 * 1024 * 1024


class UnsafeResourceError(ValueError):
    pass


def _public_addresses(host: str, port: int):
    # Reject the entire answer set when even one address is not public.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    else:
        family = socket.AF_INET6 if literal.version == 6 else socket.AF_INET
        infos = [(family, socket.SOCK_STREAM, 0, '', (str(literal), port))]
    if not infos or any(not is_safe_ip(info[4][0]) for info in infos):
        raise UnsafeResourceError('Resource host does not resolve exclusively to public addresses')
    return infos


def _connect_checked(infos, timeout: float):
    deadline = time.monotonic() + timeout
    last_error = None
    for family, socktype, proto, _, address in infos:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Resource connection timed out')
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(remaining)
            # Numeric sockaddr from the validated resolution: no DNS here.
            sock.connect(address)
            return sock
        except OSError as exc:
            sock.close()
            last_error = exc
    raise last_error or UnsafeResourceError('No resource addresses')


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, port, infos, timeout):
        super().__init__(host, port, timeout=timeout)
        self._infos = infos

    def connect(self):
        self.sock = _connect_checked(self._infos, self.timeout)
        self.transport_sock = self.sock


class _PinnedHTTPSConnection(_PinnedHTTPConnection):
    def connect(self):
        import certifi
        raw = _connect_checked(self._infos, self.timeout)
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            context.set_alpn_protocols(['http/1.1'])
            self.sock = context.wrap_socket(raw, server_hostname=self.host)
            self.transport_sock = self.sock
        except Exception:
            raw.close()
            raise


def fetch_public_bytes(url: str, *, timeout: float = 30,
                       max_bytes: int = MAX_RESOURCE_BYTES, max_redirects: int = 3):
    """Return bytes and final response headers; raise on unsafe/partial responses.

    DNS uses the OS resolver. Connection and socket reads are bounded, as is the
    response size. A deployment should also enforce an outbound network policy.
    """
    if timeout <= 0 or max_bytes <= 0 or max_redirects < 0:
        raise ValueError('Invalid resource limits')
    deadline = time.monotonic() + timeout
    for hop in range(max_redirects + 1):
        if not is_safe_url(url):
            raise UnsafeResourceError('Unsafe resource URL')
        parsed = urlsplit(url)
        host = parsed.hostname.encode('idna').decode('ascii')
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        infos = _public_addresses(host, port)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Resource request timed out')
        cls = _PinnedHTTPSConnection if parsed.scheme == 'https' else _PinnedHTTPConnection
        conn = cls(host, port, infos, remaining)
        response = None
        try:
            path = quote(parsed.path or '/', safe="/%:@!$&'()*+,;=-._~")
            if parsed.query:
                path += '?' + quote(parsed.query, safe="%/:?@!$&'()*+,;=-._~")
            conn.request('GET', path, headers={
                'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'identity',
            })
            response = conn.getresponse()
            headers = {k.lower(): v for k, v in response.getheaders()}
            if response.status in {301, 302, 303, 307, 308}:
                location = headers.get('location')
                if hop == max_redirects or not location:
                    raise UnsafeResourceError('Invalid or excessive resource redirects')
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise UnsafeResourceError(f'Resource HTTP status {response.status}')
            if headers.get('content-encoding', 'identity').lower() != 'identity':
                raise UnsafeResourceError('Compressed resource response is not supported')
            lengths = response.headers.get_all('Content-Length', [])
            if len(lengths) > 1 or (lengths and 'transfer-encoding' in headers):
                raise UnsafeResourceError('Ambiguous resource framing')
            length = int(lengths[0]) if lengths else None
            if length is not None and (length < 0 or length > max_bytes):
                raise UnsafeResourceError('Resource too large or invalid Content-Length')
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Resource read timed out')
                transport = getattr(conn, "transport_sock", None) or conn.sock
                if transport is not None:
                    transport.settimeout(remaining)
                chunk = response.read1(min(65536, max_bytes - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise UnsafeResourceError('Resource exceeds size limit')
                chunks.append(chunk)
            if size == 0 or (length is not None and size != length):
                raise UnsafeResourceError('Empty or truncated resource response')
            return b''.join(chunks), headers
        finally:
            if response is not None:
                response.close()
            conn.close()
    raise UnsafeResourceError('Too many redirects')


@contextmanager
def safe_urlopen(request, timeout=30):
    """Small urllib-compatible read seam used by the HTML image importer."""
    url = request.full_url if hasattr(request, 'full_url') else str(request)
    content, headers = fetch_public_bytes(url, timeout=timeout)
    with io.BytesIO(content) as stream:
        stream.headers = headers
        yield stream


def confined_local_path(src: str, root: Path | None) -> Path | None:
    """Resolve only regular files under an explicitly supplied trusted root."""
    if not src or root is None:
        return None
    try:
        parsed = urlsplit(src)
        if parsed.scheme not in {'', 'file'} or parsed.netloc:
            return None
        raw = unquote(parsed.path)
        if not raw or '\x00' in raw:
            return None
        base = Path(root).resolve(strict=True)
        candidate = Path(raw)
        candidate = (candidate if candidate.is_absolute() else base / candidate).resolve(strict=True)
        if candidate.is_file() and candidate.is_relative_to(base):
            return candidate
    except (OSError, ValueError, RuntimeError):
        pass
    return None


def atomic_write_resource(target: Path, content: bytes) -> None:
    """Never leave a partial download at a cacheable final path."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.download-', delete=False) as file:
            tmp = Path(file.name)
            file.write(content)
        os.replace(tmp, target)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
