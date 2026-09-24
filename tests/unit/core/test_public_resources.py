"""No real network traffic: public-resource defenses tested at the actual seams."""
from email.message import Message
import io
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from src.core import public_resources as pr
from src.core.url_safety import is_safe_ip, is_safe_url


class Response:
    def __init__(self, data=b'png', status=200, headers=()):
        self.body = io.BytesIO(data)
        self.status = status
        self.headers = Message()
        for key, value in headers:
            self.headers[key] = value
        self.closed = False

    def getheaders(self):
        return list(self.headers.items())

    def read1(self, size):
        return self.body.read(size)

    def close(self):
        self.closed = True


@pytest.fixture
def transport(monkeypatch):
    replies, connections, resolved = [], [], []

    def dns(host, port, **kwargs):
        resolved.append(host)
        ip = '10.0.0.1' if host == 'private.test' else '93.184.216.34'
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]

    def connection(host, port, infos, timeout):
        conn = Mock()
        conn.host, conn.port, conn.infos = host, port, infos
        conn.getresponse.return_value = replies.pop(0)
        connections.append(conn)
        return conn

    monkeypatch.setattr(pr.socket, 'getaddrinfo', dns)
    monkeypatch.setattr(pr, '_PinnedHTTPConnection', connection)
    monkeypatch.setattr(pr, '_PinnedHTTPSConnection', connection)
    return replies, connections, resolved


@pytest.mark.parametrize('url', [
    'http://127.0.0.1/a', 'http://[::1]/a', 'http://169.254.169.254/a',
    'http://100.64.0.1/a', 'http://224.0.0.1/a', 'http://user:secret@example.test/a',
    'http://example.test:70000/a', 'http://example.test:bad/a',
    'http://example.test/\nheader', 'http://example.test\\@localhost/a',
    'file:///etc/passwd', 'http://[fe80::1%25eth0]/a',
])
def test_unsafe_url_forms_are_rejected_before_request(url, transport):
    assert not is_safe_url(url)
    with pytest.raises(pr.UnsafeResourceError):
        pr.fetch_public_bytes(url)
    assert not transport[1]


def test_public_address_definition_excludes_shared_space_and_multicast():
    assert is_safe_ip('93.184.216.34')
    assert not is_safe_ip('100.64.0.1')
    assert not is_safe_ip('ff02::1')


def test_redirect_to_private_host_never_opens_second_connection(transport):
    replies, connections, resolved = transport
    first = Response(status=302, headers=[('Location', 'https://private.test/secret')])
    replies.append(first)
    with pytest.raises(pr.UnsafeResourceError):
        pr.fetch_public_bytes('https://public.test/a')
    assert resolved == ['public.test', 'private.test']
    assert len(connections) == 1 and first.closed
    connections[0].close.assert_called_once()


def test_redirect_to_literal_internal_ip_is_rejected(transport):
    transport[0].append(Response(status=307, headers=[('Location', 'http://127.0.0.1/a')]))
    with pytest.raises(pr.UnsafeResourceError):
        pr.fetch_public_bytes('http://public.test/a')
    assert len(transport[1]) == 1


def test_relative_public_redirect_is_followed_and_closed(transport):
    first, second = Response(status=302, headers=[('Location', '/b')]), Response(b'complete')
    transport[0].extend([first, second])
    content, _ = pr.fetch_public_bytes('https://public.test/a')
    assert content == b'complete'
    assert first.closed and second.closed
    assert transport[2] == ['public.test', 'public.test']
    assert transport[1][1].request.call_args.args[1] == '/b'


def test_mixed_public_and_private_dns_answer_is_rejected(monkeypatch):
    monkeypatch.setattr(pr.socket, 'getaddrinfo', lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.1', 443)),
    ])
    with pytest.raises(pr.UnsafeResourceError):
        pr._public_addresses('example.test', 443)


@pytest.mark.parametrize('headers,data', [
    ([('Content-Length', '100')], b'small'),
    ([], b'01234567890'),
    ([('Content-Length', '5')], b'abc'),
    ([('Content-Length', '1'), ('Content-Length', '2')], b'x'),
    ([('Content-Encoding', 'gzip')], b'encoded'),
    ([], b''),
])
def test_oversize_truncated_ambiguous_or_compressed_responses_rejected(headers, data, transport):
    response = Response(data, headers=headers)
    transport[0].append(response)
    with pytest.raises(pr.UnsafeResourceError):
        pr.fetch_public_bytes('http://public.test/a', max_bytes=10)
    assert response.closed
    transport[1][0].close.assert_called_once()


def test_socket_uses_checked_numeric_address_not_a_second_dns_resolution(monkeypatch):
    sock = Mock()
    monkeypatch.setattr(pr.socket, 'socket', Mock(return_value=sock))
    dns = Mock(side_effect=AssertionError('Must not re-resolve'))
    monkeypatch.setattr(pr.socket, 'getaddrinfo', dns)
    addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))]
    conn = pr._PinnedHTTPConnection('public.test', 80, addresses, 10)
    conn.connect()
    sock.connect.assert_called_once_with(('93.184.216.34', 80))
    dns.assert_not_called()
    conn.close()


def test_tls_still_verifies_original_hostname(monkeypatch):
    raw, secured, context = Mock(), Mock(), Mock()
    context.wrap_socket.return_value = secured
    monkeypatch.setattr(pr, '_connect_checked', Mock(return_value=raw))
    monkeypatch.setattr(pr.ssl, 'create_default_context', Mock(return_value=context))
    conn = pr._PinnedHTTPSConnection('public.test', 443, [], 10)
    conn.connect()
    context.wrap_socket.assert_called_once_with(raw, server_hostname='public.test')
    assert conn.sock is secured
    conn.close()


def test_failed_tls_closes_raw_socket(monkeypatch):
    raw, context = Mock(), Mock()
    context.wrap_socket.side_effect = OSError('certificate mismatch')
    monkeypatch.setattr(pr, '_connect_checked', Mock(return_value=raw))
    monkeypatch.setattr(pr.ssl, 'create_default_context', Mock(return_value=context))
    conn = pr._PinnedHTTPSConnection('public.test', 443, [], 10)
    with pytest.raises(OSError):
        conn.connect()
    raw.close.assert_called_once()


def test_local_image_cannot_escape_root_via_absolute_relative_or_symlink(tmp_path):
    root = tmp_path / 'root'; root.mkdir()
    inside = root / 'in.png'; inside.write_bytes(b'image')
    outside = tmp_path / 'secret.png'; outside.write_bytes(b'private')
    (root / 'escape.png').symlink_to(outside)
    assert pr.confined_local_path('in.png', root) == inside
    for src in ('../secret.png', str(outside), outside.as_uri(), 'escape.png', 'file://other/in.png'):
        assert pr.confined_local_path(src, root) is None
    assert pr.confined_local_path(str(inside), None) is None


def test_html_importer_refuses_external_local_files(tmp_path):
    from src.html2md.images import _copy_image
    root = tmp_path / 'root'; root.mkdir()
    source = root / 'article.html'; source.write_text('')
    (tmp_path / 'secret.png').write_bytes(b'private')
    destination = root / 'output.png'
    assert not _copy_image('../secret.png', source, destination)
    assert not destination.exists()


def test_failed_download_leaves_no_cached_partial_file(tmp_path, monkeypatch):
    from src.core.image_downloader import ImageDownloader
    def interrupted(*a, **kw):
        raise OSError('connection interrupted')
    monkeypatch.setattr('src.core.image_downloader.fetch_public_bytes', interrupted)
    downloader = ImageDownloader(images_dir=str(tmp_path / 'images'))
    assert downloader.download('https://public.test/img.png') is None
    assert not list((tmp_path / 'images').glob('*'))


def test_atomic_file_failure_cleans_temp_and_preserves_original(tmp_path, monkeypatch):
    target = tmp_path / 'image.png'; target.write_bytes(b'old')
    monkeypatch.setattr(pr.os, 'replace', Mock(side_effect=OSError('disk error')))
    with pytest.raises(OSError):
        pr.atomic_write_resource(target, b'new')
    assert target.read_bytes() == b'old'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['image.png']


def test_wechat_local_resource_returns_owned_copy_never_deletes_source(tmp_path, monkeypatch):
    from src.services.wechat_formatter import WechatFormatter
    monkeypatch.chdir(tmp_path)
    images = Path('projects/p/images'); images.mkdir(parents=True)
    source = images / 'ok.png'; source.write_bytes(b'image')
    formatter = WechatFormatter.__new__(WechatFormatter); formatter.project_id = 'p'
    temp = formatter._download_image_sync('/api/projects/p/assets/images/ok.png')
    assert temp and Path(temp).read_bytes() == b'image'
    Path(temp).unlink()  # same ownership contract as upload/base64 callers
    assert source.read_bytes() == b'image'
    secret = Path('secret.png'); secret.write_bytes(b'private')
    assert formatter._download_image_sync(str(secret.resolve())) is None
    (Path('projects/p') / 'meta.json').write_text('{"private": true}')
    assert formatter._download_image_sync('/api/projects/p/assets/meta.json') is None
