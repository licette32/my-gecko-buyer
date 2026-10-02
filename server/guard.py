"""The guard: decide on the string, before any socket opens.

Standard library only. A URL is public only if it is https and its host is,
or resolves to, a public address.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

#: The private, loopback, link-local, reserved and multicast ranges.
_BLOCKED_FLAGS = (
    "is_private",
    "is_loopback",
    "is_link_local",
    "is_multicast",
    "is_reserved",
    "is_unspecified",
)


def _is_public_address(host: str) -> bool:
    """True if `host` is a public address, or a name that resolves to one."""
    # 1. The host as an IP literal, if it parses.
    try:
        addr = ipaddress.ip_address(host)
        return not any(getattr(addr, flag) for flag in _BLOCKED_FLAGS)
    except ValueError:
        pass

    # 2. The host is a name. Resolve it and check every address that comes back.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Decision: a name that does not resolve is refused. A guard that
        # shrugs hands the decision to a client with no rules to decide it.
        return False
    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if any(getattr(addr, flag) for flag in _BLOCKED_FLAGS):
            return False
    return True


def is_public_url(url: str) -> bool:
    """True only for an https URL whose host is, or resolves to, a public address."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme != "https":
        return False
    host = parts.hostname
    if not host:
        return False
    return _is_public_address(host)
