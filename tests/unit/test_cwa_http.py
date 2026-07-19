import ssl
from unittest.mock import MagicMock, patch

from infrastructure.cwa_http import _cwa_ssl_context, fetch_bytes


def test_context_clears_strict_x509_flag():
    # CWA's chain is missing the Subject Key Identifier extension; the Python
    # 3.13+ strict default would reject the handshake.
    ctx = _cwa_ssl_context()
    assert not ctx.verify_flags & ssl.VERIFY_X509_STRICT


def test_context_keeps_chain_and_hostname_verification():
    ctx = _cwa_ssl_context()
    assert ctx.check_hostname is True
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_fetch_bytes_uses_relaxed_context_and_returns_body():
    resp = MagicMock()
    resp.__enter__.return_value.read.return_value = b"payload"
    with patch("infrastructure.cwa_http.urlopen", return_value=resp) as mock_open:
        assert fetch_bytes("https://example.test/x", timeout=7) == b"payload"
    args, kwargs = mock_open.call_args
    assert args[0] == "https://example.test/x"
    assert kwargs["timeout"] == 7
    assert not kwargs["context"].verify_flags & ssl.VERIFY_X509_STRICT
