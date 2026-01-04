import json
from pathlib import Path
import pytest
from unittest.mock import patch

import aiohttp

from custom_components.greencell_ups.api import (
    GreencellApi,
    GreencellAuthError,
    GreencellRequestError,
    GreencellResponseError,
)


SAMPLES_DIR = Path(__file__).parent / "samples"

def _load_sample(name: str):
    return json.loads((SAMPLES_DIR / name).read_text())

SAMPLE_STATUS = _load_sample("current_parameters.json")
SAMPLE_SPEC = _load_sample("specification.json")
SAMPLE_TESTS = _load_sample("statistics_tests.json")
SAMPLE_TEST_MEASUREMENTS = _load_sample("statistics_test_measurements.json")
SAMPLE_EVENTS = _load_sample("statistics_events.json")
SAMPLE_SCHEDULES = _load_sample("schedules.json")
SAMPLE_SMTP = _load_sample("smtp_settings.json")
SAMPLE_SMTP_VERIFY = _load_sample("smtp_verify.json")


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
        self.last_verify_payload = None

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
        if method == "GET" and path == "/api/device/specification":
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
        if method == "GET" and path == "/api/statistics/tests":
            return DummyResponse(200, SAMPLE_TESTS)
        if method == "GET" and path == "/api/statistics/tests/test-long/measurements":
            return DummyResponse(200, SAMPLE_TEST_MEASUREMENTS)
        if method == "GET" and path == "/api/statistics/events?limit=1000":
            return DummyResponse(200, SAMPLE_EVENTS)
        if method == "GET" and path == "/api/scheduler/schedules?visible=true":
            return DummyResponse(200, SAMPLE_SCHEDULES)
        if method == "GET" and path == "/api/settings/smtp":
            return DummyResponse(200, SAMPLE_SMTP)
        if method == "PUT" and path == "/api/settings/smtp":
            self.last_verify_payload = json
            return DummyResponse(200, SAMPLE_SMTP)
        if method == "POST" and path == "/api/settings/smtp/verify":
            self.last_verify_payload = json
            return DummyResponse(200, SAMPLE_SMTP_VERIFY)
        if method == "DELETE" and path.startswith("/api/scheduler/schedules/"):
            return DummyResponse(200, True)
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


@pytest.mark.asyncio
async def test_fetch_statistics(monkeypatch):
    session = DummySession()
    monkeypatch.setattr('aiohttp.ClientSession', lambda: session)
    api = GreencellApi("http://host", "pw")
    tests = await api.fetch_statistics_tests()
    assert tests == SAMPLE_TESTS

    measurements = await api.fetch_test_measurements("test-long")
    assert measurements == SAMPLE_TEST_MEASUREMENTS

    events = await api.fetch_statistics_events()
    assert events == SAMPLE_EVENTS

    schedules = await api.fetch_schedules()
    assert schedules == SAMPLE_SCHEDULES

    smtp = await api.fetch_smtp_settings()
    assert smtp == SAMPLE_SMTP

    smtp_update = await api.update_smtp_settings(SAMPLE_SMTP)
    assert smtp_update == SAMPLE_SMTP

    smtp_verify = await api.verify_smtp_settings(SAMPLE_SMTP)
    assert smtp_verify == SAMPLE_SMTP_VERIFY
    assert session.last_verify_payload == SAMPLE_SMTP

    deleted = await api.delete_schedule("sched-1")
    assert deleted is True
