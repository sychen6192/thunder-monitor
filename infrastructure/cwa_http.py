"""Shared HTTP fetch for CWA endpoints (open-data files and the radar image).

CWA's certificate chain violates RFC 5280 — a chain certificate is missing the
Subject Key Identifier extension. Python 3.13+ enables VERIFY_X509_STRICT by
default and rejects the handshake, so fetches here use a context that keeps
chain-of-trust and hostname verification but drops the strict RFC conformance
checks (the pre-3.13 default behavior).
"""

import ssl
import time
from urllib.request import urlopen


def _cwa_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return ctx


_CONTEXT = _cwa_ssl_context()


def fetch_bytes(url: str, timeout: float = 15, attempts: int = 3, backoff: float = 0.5) -> bytes:
    """GET ``url`` and return the response body, retrying transient failures.

    CWA's file endpoints are flaky — timeouts, sporadic 5xx, TLS resets — and a
    single blip should not fail a whole detection round. Retries up to
    ``attempts`` times with linear backoff (``backoff * attempt`` seconds), and
    re-raises the last error only after every attempt fails. The GET is
    idempotent, so retrying is safe. Callers run this off the event loop (via
    ``asyncio.to_thread``), so the blocking sleep never stalls the daemon.
    """
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(url, timeout=timeout, context=_CONTEXT) as resp:
                return resp.read()
        except Exception:  # timeout, HTTP 5xx, TLS reset — retry transient CWA failures
            if attempt >= attempts:
                raise
            time.sleep(backoff * attempt)
    raise RuntimeError("unreachable")  # attempts >= 1 always returns or raises above
