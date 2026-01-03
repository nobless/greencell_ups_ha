import pytest
from unittest.mock import patch

import aiohttp

from custom_components.greencell_ups.api import (
    GreencellApi,
    GreencellAuthError,
    GreencellRequestError,
    GreencellResponseError,
)


SAMPLE_STATUS = {
    "inputVoltage": 228.5,
    "inputVoltageFault": 228.5,
    "outputVoltage": 228.5,
    "load": 2,
    "inputFrequency": 50.1,
    "batteryVoltage": 13.1,
    "temperature": -1,
    "utilityFail": False,
    "batteryLow": False,
    "bypassBoost": False,
    "failed": False,
    "offline": True,
    "testInProgress": False,
    "shutdownActive": False,
    "beeperOn": False,
    "batteryLevel": 100,
    "active": True,
    "connected": True,
    "status": 0,
    "register": [],
    "issues": [],
    "errno": 0,
    "inputVoltageNominal": 230,
    "inputFrequencyNominal": 50,
    "batteryVoltageNominal": 12,
    "inputCurrentNominal": 3,
    "batteryNumberNominal": 1,
    "batteryVoltageHighNominal": 12.600000000000001,
    "batteryVoltageLowNominal": 10.98,
    "reg": 8,
}

SAMPLE_SPEC = {
    "name": "PowerProof/AiO",
    "codes": [
        "UPS02",
        "UPS07"
    ],
    "inf": "",
    "description": "\"UPS02=3A 12V\", \"UPS07=3A 12V\"",
    "online": False,
    "sinus": False,
    "power": 480,
    "capacity": 800,
    "batteryType": 9,
    "batteryNumber": 1,
    "batteryVoltage": 12,
    "current": 3
}


class DummyResponse:
    def __init__(self, status, json_data):
        self.status = status
        self._json = json_data
        self._text = None

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

    async def text(self):
        if self._text is not None:
            return self._text
        return str(self._json)


class DummySession:
    def __init__(self):
        self.get_calls = 0
        self.spec_calls = 0
        self.command_calls = 0

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
            return DummyResponse(200, SAMPLE_STATUS)
        if method == "GET" and path == "/api/specification":
            self.spec_calls += 1
            if self.spec_calls == 1:
                return DummyResponse(401, {})
            return DummyResponse(200, SAMPLE_SPEC)
        if method == "GET" and path == "/api/error":
            return DummyResponse(500, {})
        if method == "POST" and path == "/api/commands":
            self.command_calls += 1
            if json and json.get("action") in {
                "beeperToggleOrder",
                "shutdownOrder",
                "wakeUpOrder",
                "shortTestOrder",
                "longTestOrder",
                "cancelTestOrder",
            }:
                return DummyResponse(200, 1)
            return DummyResponse(400, {})
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
    assert data == SAMPLE_STATUS
    assert api._token == "tok"


@pytest.mark.asyncio
async def test_fetch_specification_reauths_on_401(monkeypatch):
    monkeypatch.setattr('aiohttp.ClientSession', lambda: DummySession())
    api = GreencellApi("http://host", "pw")
    api._token = "expired"
    data = await api.fetch_specification()
    assert data == SAMPLE_SPEC
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


@pytest.mark.asyncio
async def test_toggle_beeper(monkeypatch):
    session = DummySession()
    monkeypatch.setattr('aiohttp.ClientSession', lambda: session)
    api = GreencellApi("http://host", "pw")
    api._token = "tok"
    resp = await api.toggle_beeper()
    assert resp == 1  # Commands return 1 on success
    assert session.command_calls >= 1


@pytest.mark.asyncio
async def test_shutdown_wakeup_short_test(monkeypatch):
    session = DummySession()
    monkeypatch.setattr('aiohttp.ClientSession', lambda: session)
    api = GreencellApi("http://host", "pw")
    api._token = "tok"

    assert await api.shutdown() == 1
    assert await api.wake_up() == 1
    assert await api.short_test() == 1
    assert await api.long_test() == 1
    assert await api.cancel_test() == 1
    assert session.command_calls >= 5


@pytest.mark.asyncio
async def test_command_text_response(monkeypatch):
    class TextDummy(DummyResponse):
        def __init__(self, status, json_data, text_data):
            super().__init__(status, json_data)
            self._text = text_data

    class TextSession(DummySession):
        def request(self, method, url, json=None, headers=None):
            path = url.replace("http://host", "")
            if method == "POST" and path == "/api/login":
                return DummyResponse(200, {"access_token": "tok"})
            if method == "POST" and path == "/api/commands":
                return TextDummy(200, {"unexpected": True}, "1")
            return DummyResponse(404, {})

    monkeypatch.setattr('aiohttp.ClientSession', lambda: TextSession())
    api = GreencellApi("http://host", "pw")
    api._token = "tok"
    result = await api.toggle_beeper()
    assert result == 1
