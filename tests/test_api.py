import pytest
from unittest.mock import patch

import aiohttp

from custom_components.greencell_ups.api import (
    GreencellApi,
    GreencellAuthError,
    GreencellRequestError,
    GreencellResponseError,
)


class DummyResponse:
    def __init__(self, status, json_data):
        self.status = status
        self._json = json_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        if self.status >= 400 and self.status != 401:
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=self.status,
                message="HTTP error",
                headers=None,
            )

    async def json(self):
        return self._json


class DummySession:
    def __init__(self):
        self.get_calls = 0
        self.spec_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def request(self, method, url, json=None, headers=None):
        # Strip host prefix so we can inspect path easily
        path = url.replace("http://host", "")
        if method == "POST" and path == "/api/login":
            if json and json.get("password") == "missing":
                return DummyResponse(200, {})
            return DummyResponse(200, {"access_token": "tok"})
        if method == "GET" and path == "/api/current_parameters":
            self.get_calls += 1
            # First GET simulates an expired token (401), subsequent GETs succeed
            if self.get_calls == 1:
                return DummyResponse(401, {})
            return DummyResponse(200, {"ok": True})
        if method == "GET" and path == "/api/specification":
            self.spec_calls += 1
            if self.spec_calls == 1:
                return DummyResponse(401, {})
            return DummyResponse(200, {"name": "PowerProof", "codes": ["UPS02"]})
        if method == "GET" and path == "/api/error":
            return DummyResponse(500, {})
        return DummyResponse(404, {})


@pytest.mark.asyncio
async def test_login_sets_token(monkeypatch):
    monkeypatch.setattr('aiohttp.ClientSession', lambda: DummySession())
    api = GreencellApi("http://host", "pw")
    await api.login()
    assert api._token == "tok"


@pytest.mark.asyncio
async def test_fetch_status_reauths_on_401(monkeypatch):
    monkeypatch.setattr('aiohttp.ClientSession', lambda: DummySession())
    api = GreencellApi("http://host", "pw")
    # simulate expired token so the first GET returns 401 and triggers re-login
    api._token = "expired"
    data = await api.fetch_status()
    assert data == {"ok": True}
    assert api._token == "tok"


@pytest.mark.asyncio
async def test_fetch_specification_reauths_on_401(monkeypatch):
    monkeypatch.setattr('aiohttp.ClientSession', lambda: DummySession())
    api = GreencellApi("http://host", "pw")
    api._token = "expired"
    data = await api.fetch_specification()
    assert data == {"name": "PowerProof", "codes": ["UPS02"]}
    assert api._token == "tok"


@pytest.mark.asyncio
async def test_request_raises_on_http_error(monkeypatch):
    monkeypatch.setattr('aiohttp.ClientSession', lambda: DummySession())
    api = GreencellApi("http://host", "pw")
    with pytest.raises(GreencellRequestError):
        await api._request("GET", "/api/error")


@pytest.mark.asyncio
async def test_login_missing_token(monkeypatch):
    monkeypatch.setattr('aiohttp.ClientSession', lambda: DummySession())
    api = GreencellApi("http://host", "missing")
    with pytest.raises(GreencellResponseError):
        await api.login()
