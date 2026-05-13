"""
Network restriction enforcer.
Monkey-patches urllib and requests/httpx to enforce allowlist/denylist.
"""

from __future__ import annotations
import fnmatch
from urllib.parse import urlparse
from ..exceptions import NetworkBlockedError


def _host_matches(host: str, pattern: str) -> bool:
    """Match host against a pattern like '*.evil.com' or 'evil.com'."""
    if fnmatch.fnmatch(host, pattern):
        return True
    # *.evil.com should match evil.com and sub.evil.com
    if pattern.startswith("*."):
        base = pattern[2:]
        if host == base or host.endswith("." + base):
            return True
    return False


def _extract_host(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def check_url(url: str, mode: str, allow: list[str], deny: list[str]):
    """
    Check if a URL is allowed by the network config.
    Raises NetworkBlockedError if blocked.
    """
    host = _extract_host(url)

    # Deny list always applies regardless of mode
    for pattern in deny:
        if _host_matches(host, pattern):
            raise NetworkBlockedError(url, f"host matches deny pattern {pattern!r}")

    if mode == "open":
        return

    if mode == "disabled":
        raise NetworkBlockedError(url, "network access is disabled")

    if mode == "restricted":
        for pattern in allow:
            if _host_matches(host, pattern):
                return
        raise NetworkBlockedError(url, f"host {host!r} not in allowlist")


class NetworkEnforcer:
    """
    Wraps urllib.request.urlopen and optionally requests/httpx
    to enforce network restrictions at runtime.
    """

    def __init__(self, mode: str, allow: list[str], deny: list[str]):
        self.mode = mode
        self.allow = allow
        self.deny = deny
        self._patches: list = []

    def install(self):
        """Install monkey-patches."""
        if self.mode == "open" and not self.deny:
            return  # Nothing to enforce

        self._patch_urllib()
        self._patch_requests()
        self._patch_httpx()

    def uninstall(self):
        """Remove monkey-patches."""
        for restore_fn in self._patches:
            restore_fn()
        self._patches.clear()

    def _patch_urllib(self):
        try:
            import urllib.request as urllib_request
            original = urllib_request.urlopen

            mode, allow, deny = self.mode, self.allow, self.deny

            def guarded_urlopen(url, *args, **kwargs):
                url_str = url if isinstance(url, str) else getattr(url, "full_url", str(url))
                check_url(url_str, mode, allow, deny)
                return original(url, *args, **kwargs)

            urllib_request.urlopen = guarded_urlopen
            self._patches.append(lambda: setattr(urllib_request, "urlopen", original))
        except Exception:
            pass

    def _patch_requests(self):
        try:
            import requests
            original = requests.Session.request

            mode, allow, deny = self.mode, self.allow, self.deny

            def guarded_request(self_session, method, url, **kwargs):
                check_url(url, mode, allow, deny)
                return original(self_session, method, url, **kwargs)

            requests.Session.request = guarded_request
            self._patches.append(lambda: setattr(requests.Session, "request", original))
        except ImportError:
            pass

    def _patch_httpx(self):
        try:
            import httpx
            original = httpx.Client.send

            mode, allow, deny = self.mode, self.allow, self.deny

            def guarded_send(self_client, request, **kwargs):
                check_url(str(request.url), mode, allow, deny)
                return original(self_client, request, **kwargs)

            httpx.Client.send = guarded_send
            self._patches.append(lambda: setattr(httpx.Client, "send", original))
        except ImportError:
            pass
