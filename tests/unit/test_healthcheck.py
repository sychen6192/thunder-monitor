from unittest.mock import patch

import httpx

from infrastructure.healthcheck import ping


class _FakeClient:
    """Records GET urls; stands in for httpx.AsyncClient."""

    calls: list = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url):
        _FakeClient.calls.append(url)


async def test_ping_success_gets_base_url():
    _FakeClient.calls = []
    with patch("infrastructure.healthcheck.httpx.AsyncClient", _FakeClient):
        await ping("https://hc-ping.com/abc")
    assert _FakeClient.calls == ["https://hc-ping.com/abc"]


async def test_ping_fail_hits_fail_endpoint():
    _FakeClient.calls = []
    with patch("infrastructure.healthcheck.httpx.AsyncClient", _FakeClient):
        await ping("https://hc-ping.com/abc", fail=True)
    assert _FakeClient.calls == ["https://hc-ping.com/abc/fail"]


async def test_ping_strips_trailing_slash_before_fail_suffix():
    _FakeClient.calls = []
    with patch("infrastructure.healthcheck.httpx.AsyncClient", _FakeClient):
        await ping("https://hc-ping.com/abc/", fail=True)
    assert _FakeClient.calls == ["https://hc-ping.com/abc/fail"]


async def test_ping_empty_url_makes_no_request():
    _FakeClient.calls = []
    with patch("infrastructure.healthcheck.httpx.AsyncClient", _FakeClient):
        await ping("")
    assert _FakeClient.calls == []


async def test_ping_swallows_network_errors():
    class _Failing(_FakeClient):
        async def get(self, url):
            raise httpx.ConnectError("boom")

    with patch("infrastructure.healthcheck.httpx.AsyncClient", _Failing):
        await ping("https://hc-ping.com/abc")  # must not raise
