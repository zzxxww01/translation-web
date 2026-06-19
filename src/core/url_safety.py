"""
URL / IP 安全工具:防 SSRF(内网/回环/链路本地/保留地址)与 DNS-rebinding。

集中实现,供所有"按外部可控 URL 抓取资源"的链路(图片下载等)复用,
避免各处重复实现校验逻辑而产生不一致的安全缺口。
"""

import ipaddress
import socket
from urllib.parse import urlparse


def is_safe_ip(ip_str: str) -> bool:
    """IP 是否为可安全访问的公网地址(排除私有/回环/链路本地/保留/多播/未指定)。"""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def is_safe_url(url: str) -> bool:
    """请求前的快速预检:仅放行 http/https,且字面 IP 主机必须安全。"""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname.lower() == "localhost":
        return False
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        # 域名:留待 resolved_ips_are_safe 在连接前解析校验
        return True
    return is_safe_ip(hostname)


def resolved_ips_are_safe(url: str) -> bool:
    """
    解析 URL 主机的所有 IP 并逐个校验。

    线程安全(无任何进程级全局可变状态),用于在请求前阻断解析到内网/云元数据
    地址的 SSRF。注:与请求库自身的二次解析之间仍有 TOCTOU 窗口,完整的
    DNS-rebinding 防护需在连接时 pin IP;此函数已消除"全局 monkeypatch 竞态"类缺陷。
    """
    hostname = urlparse(url).hostname
    if not hostname:
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    return all(is_safe_ip(info[4][0]) for info in infos)
