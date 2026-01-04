import asyncio
import logging
from typing import Optional

import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)


class GreencellApiError(Exception):
    """Base error for Greencell API issues."""


class GreencellAuthError(GreencellApiError):
    """Authentication failed or token expired."""


class GreencellRequestError(GreencellApiError):
    """Transport or HTTP error while talking to the API."""


class GreencellResponseError(GreencellApiError):
    """Response payload was invalid or missing required fields."""


class GreencellApi:
    def __init__(
        self,
        host: str,
        password: str,
        session: Optional[aiohttp.ClientSession] = None,
        verify_ssl: bool = False,
    ):
        self._host = host.rstrip("/")
        self._password = password
        self._token = None
        self._session = session
        self._verify_ssl = verify_ssl

    async def _request(self, method, path, json=None, session=None, expect_json=True):
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        active_session = session or self._session
        close_session = False
        if active_session is None:
            active_session = aiohttp.ClientSession()
            close_session = True

        try:
            _LOGGER.debug("HTTP %s %s (json=%s)", method, path, bool(json))
            async with async_timeout.timeout(10):
                async with active_session.request(
                    method,
                    f"{self._host}{path}",
                    json=json,
                    headers=headers,
                    ssl=self._verify_ssl,
                ) as resp:
                    if resp.status == 401:
                        self._token = None
                        raise GreencellAuthError("Unauthorized")
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as err:
                        raise GreencellRequestError(
                            f"HTTP error {err.status}: {err.message}"
                        ) from err
                    if expect_json:
                        try:
                            return await resp.json()
                        except Exception as err:
                            raise GreencellResponseError("Invalid JSON response") from err
                    else:
                        try:
                            return await resp.json()
                        except Exception:
                            text = await resp.text()
                            stripped = text.strip()
                            if stripped.isdigit():
                                return int(stripped)
                            return stripped or text
            _LOGGER.debug("HTTP %s %s completed", method, path)
        except asyncio.TimeoutError as err:
            raise GreencellRequestError("Request timed out") from err
        except aiohttp.ClientError as err:
            raise GreencellRequestError("Request failed") from err
        finally:
            if close_session and hasattr(active_session, "close"):
                close_result = active_session.close()
                if asyncio.iscoroutine(close_result):
                    await close_result

    async def login(self, session=None):
        data = await self._request(
            "POST",
            "/api/login",
            json={"password": self._password},
            session=session,
        )
        try:
            self._token = data["access_token"]
        except Exception as err:
            raise GreencellResponseError("Login response missing access_token") from err

    async def _with_session(self, func):
        if self._session:
            return await func(self._session)
        async with aiohttp.ClientSession() as session:
            return await func(session)

    async def fetch_specification(self):
        async def _execute(session):
            if not self._token:
                await self.login(session=session)

            try:
                try:
                    return await self._request("GET", "/api/specification", session=session)
                except GreencellRequestError:
                    return await self._request("GET", "/api/device/specification", session=session)
            except GreencellAuthError:
                await self.login(session=session)
                try:
                    return await self._request("GET", "/api/specification", session=session)
                except GreencellRequestError:
                    return await self._request("GET", "/api/device/specification", session=session)

        return await self._with_session(_execute)

    async def fetch_status(self):
        async def _execute(session):
            if not self._token:
                await self.login(session=session)

            try:
                return await self._request(
                    "GET", "/api/current_parameters", session=session
                )
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request(
                    "GET", "/api/current_parameters", session=session
                )

        return await self._with_session(_execute)

    async def toggle_beeper(self):
        """Toggle UPS beeper on/off."""
        return await self._send_command("beeperToggleOrder")

    async def shutdown(self):
        """Send shutdown order; UPS goes to sleep until wake-up."""
        return await self._send_command("shutdownOrder")

    async def wake_up(self):
        """Wake the UPS after shutdown."""
        return await self._send_command("wakeUpOrder")

    async def short_test(self):
        """Run a short UPS self-test (~10s)."""
        return await self._send_command("shortTestOrder")

    async def long_test(self):
        """Run a long battery discharge test."""
        return await self._send_command("longTestOrder")

    async def cancel_test(self):
        """Cancel an active discharge/self-test cycle."""
        return await self._send_command("cancelTestOrder")

    async def fetch_statistics_tests(self):
        """Fetch history of UPS tests."""
        async def _execute(session):
            if not self._token:
                await self.login(session=session)
            try:
                return await self._request(
                    "GET", "/api/statistics/tests", session=session
                )
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request(
                    "GET", "/api/statistics/tests", session=session
                )

        return await self._with_session(_execute)

    async def fetch_test_measurements(self, test_id: str):
        """Fetch measurements for a specific test run."""
        async def _execute(session):
            if not self._token:
                await self.login(session=session)
            path = f"/api/statistics/tests/{test_id}/measurements"
            try:
                return await self._request("GET", path, session=session)
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request("GET", path, session=session)

        return await self._with_session(_execute)

    async def fetch_statistics_events(self, limit: int = 1000):
        """Fetch event history."""
        async def _execute(session):
            if not self._token:
                await self.login(session=session)
            path = f"/api/statistics/events?limit={limit}"
            try:
                return await self._request("GET", path, session=session)
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request("GET", path, session=session)

        return await self._with_session(_execute)

    async def fetch_schedules(self, visible: bool = True):
        """Fetch schedules."""
        async def _execute(session):
            if not self._token:
                await self.login(session=session)
            suffix = "?visible=true" if visible else ""
            path = f"/api/scheduler/schedules{suffix}"
            try:
                return await self._request("GET", path, session=session)
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request("GET", path, session=session)

        return await self._with_session(_execute)

    async def delete_schedule(self, schedule_id: str):
        """Delete a schedule by id."""
        async def _execute(session):
            if not self._token:
                await self.login(session=session)
            path = f"/api/scheduler/schedules/{schedule_id}"
            try:
                return await self._request("DELETE", path, session=session)
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request("DELETE", path, session=session)

        return await self._with_session(_execute)

    async def fetch_smtp_settings(self):
        """Fetch SMTP settings."""
        async def _execute(session):
            if not self._token:
                await self.login(session=session)
            try:
                return await self._request("GET", "/api/settings/smtp", session=session)
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request("GET", "/api/settings/smtp", session=session)

        return await self._with_session(_execute)

    async def update_smtp_settings(self, payload: dict):
        """Update SMTP settings."""
        async def _execute(session):
            if not self._token:
                await self.login(session=session)
            try:
                return await self._request(
                    "PUT", "/api/settings/smtp", json=payload, session=session
                )
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request(
                    "PUT", "/api/settings/smtp", json=payload, session=session
                )

        return await self._with_session(_execute)

    async def verify_smtp_settings(self, payload: dict):
        """Verify SMTP settings."""
        async def _execute(session):
            if not self._token:
                await self.login(session=session)
            try:
                return await self._request(
                    "POST", "/api/settings/smtp/verify", json=payload, session=session
                )
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request(
                    "POST", "/api/settings/smtp/verify", json=payload, session=session
                )

        return await self._with_session(_execute)

    async def _send_command(self, action: str):
        async def _execute(session):
            if not self._token:
                await self.login(session=session)

            payload = {"action": action, "args": {}}
            _LOGGER.debug("Sending command to /api/commands: action=%s", action)
            try:
                resp = await self._request(
                    "POST",
                    "/api/commands",
                    json=payload,
                    session=session,
                    expect_json=False,
                )
                _LOGGER.debug(
                    "Command action=%s succeeded with response=%s", action, resp
                )
                return resp
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request(
                    "POST",
                    "/api/commands",
                    json=payload,
                    session=session,
                    expect_json=False,
                )
        try:
            return await self._with_session(_execute)
        except GreencellApiError as err:
            _LOGGER.debug("Command %s failed at /api/commands: %s", action, err)
            raise
