"""core/network.py — local IPv4 address discovery.

get_local_ips() returns the machine's IPv4 addresses with loopback
(127.0.0.1) always first, followed by sorted LAN addresses.
No bpy dependency.
"""
from __future__ import annotations

import socket


def get_local_ips() -> list[str]:
    """Return local IPv4 addresses: loopback first, then sorted LAN IPs."""
    loopback = "127.0.0.1"
    seen: set[str] = set()
    lan: list[str] = []

    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        for family, _type, _proto, _canonname, sockaddr in infos:
            if family != socket.AF_INET:
                continue
            ip = sockaddr[0]
            if ip == loopback or ip in seen:
                continue
            seen.add(ip)
            lan.append(ip)
    except OSError:
        pass

    return [loopback] + sorted(lan)
