import asyncio
from typing import Optional

import aiohttp
import async_timeout


class GreencellApiError(Exception):
    """Base error for Greencell API issues."""


class GreencellAuthError(GreencellApiError):
    """Authentication failed or token expired."""


class GreencellRequestError(GreencellApiError):
    """Transport or HTTP error while talking to the API."""


class GreencellResponseError(GreencellApiError):
    """Response payload was invalid or missing required fields."""


class GreencellApi:
    def __init__(self, host: str, password: str, session: Optional[aiohttp.ClientSession] = None):
        self._host = host.rstrip("/")
        self._password = password
        self._token = None
        self._session = session

    async def _request(self, method, path, json=None, session=None):
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        active_session = session or self._session
        close_session = False
        if active_session is None:
            active_session = aiohttp.ClientSession()
            close_session = True

        try:
            async with async_timeout.timeout(10):
                async with active_session.request(
                    method,
                    f"{self._host}{path}",
                    json=json,
                    headers=headers,
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
                    try:
                        return await resp.json()
                    except Exception as err:
                        raise GreencellResponseError("Invalid JSON response") from err
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
                return await self._request("GET", "/api/specification", session=session)
            except GreencellAuthError:
                await self.login(session=session)
                return await self._request(
                    "GET", "/api/specification", session=session
                )

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
