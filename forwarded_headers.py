"""Strict public-origin helpers for explicitly trusted proxy deployments."""

from __future__ import annotations

from typing import Callable
from urllib.parse import urlsplit


def _normalize_host(value: str, scheme: str | None = None) -> str | None:
    if not value or value.endswith(":") or any(char in value for char in "\r\n\t ,/@?#\\"):
        return None
    parsed = urlsplit("//" + value)
    if (
        parsed.username is not None
        or parsed.password is not None
        or not parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    hostname = parsed.hostname.casefold()
    if ":" in hostname:
        hostname = f"[{hostname}]"
    default_port = 80 if scheme == "http" else 443 if scheme == "https" else None
    if port is not None and port != default_port:
        hostname = f"{hostname}:{port}"
    return hostname


def normalize_origin(value: str) -> tuple[str, str] | None:
    """Return a normalized HTTP(S) origin, rejecting non-origin URL parts."""
    if not value or value != value.strip() or any(c in value for c in "\r\n\t"):
        return None
    parsed = urlsplit(value)
    scheme = parsed.scheme.casefold()
    if (
        scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    host = _normalize_host(parsed.netloc, scheme)
    return (scheme, host) if host else None


def _header_values(scope: dict, name: bytes) -> list[bytes]:
    return [value for key, value in scope.get("headers", []) if key.lower() == name]


def _direct_origin(scope: dict) -> tuple[str, str]:
    scheme = str(scope.get("scheme", "http")).casefold()
    if scheme not in {"http", "https"}:
        scheme = "http"
    hosts = _header_values(scope, b"host")
    raw_host = hosts[0].decode("latin-1") if len(hosts) == 1 else ""
    host = _normalize_host(raw_host, scheme)
    if not host:
        server = scope.get("server")
        if server:
            raw_host = str(server[0])
            if server[1] is not None and int(server[1]) not in {80, 443}:
                raw_host = f"{raw_host}:{server[1]}"
            host = _normalize_host(raw_host, scheme)
    return scheme, host or ""


def _forwarded_origin(scope: dict) -> tuple[str, str] | None:
    protos = _header_values(scope, b"x-forwarded-proto")
    hosts = _header_values(scope, b"x-forwarded-host")
    if len(protos) != 1 or len(hosts) != 1:
        return None
    try:
        scheme = protos[0].decode("ascii").casefold()
        raw_host = hosts[0].decode("ascii")
    except UnicodeDecodeError:
        return None
    host = _normalize_host(raw_host, scheme)
    if scheme not in {"http", "https"} or host is None:
        return None
    return scheme, host


def public_origin(scope: dict, trusted_proxy: bool) -> tuple[str, str]:
    """Resolve the request origin; forwarding values require out-of-band trust."""
    if trusted_proxy:
        forwarded = _forwarded_origin(scope)
        if forwarded:
            return forwarded
    return _direct_origin(scope)


class ForwardedOriginMiddleware:
    """Apply forwarding headers only when an external trust check says so."""

    def __init__(self, app, trust_proxy: Callable[[dict], bool]):
        self.app = app
        self.trust_proxy = trust_proxy

    async def __call__(self, scope, receive, send):
        if scope.get("type") in {"http", "websocket"}:
            try:
                trusted = bool(self.trust_proxy(scope))
            except Exception:
                trusted = False
            if trusted:
                origin = _forwarded_origin(scope)
                if origin:
                    scheme, host = origin
                    scope = dict(scope)
                    scope["scheme"] = scheme
                    scope["headers"] = [
                        (key, value)
                        for key, value in scope.get("headers", [])
                        if key.lower() != b"host"
                    ] + [(b"host", host.encode("ascii"))]
        await self.app(scope, receive, send)
