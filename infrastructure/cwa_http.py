"""Shared HTTP fetch for CWA endpoints (open-data files and the radar image).

CWA's certificate chain violates RFC 5280 — a chain certificate is missing the
Subject Key Identifier extension. Python 3.13+ enables VERIFY_X509_STRICT by
default and rejects the handshake, so fetches here use a context that keeps
chain-of-trust and hostname verification but drops the strict RFC conformance
checks (the pre-3.13 default behavior).
"""

import ssl
from urllib.request import urlopen


def _cwa_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return ctx


_CONTEXT = _cwa_ssl_context()


def fetch_bytes(url: str, timeout: float = 15) -> bytes:
    """GET ``url`` and return the response body; raises on HTTP or TLS errors."""
    with urlopen(url, timeout=timeout, context=_CONTEXT) as resp:
        return resp.read()
