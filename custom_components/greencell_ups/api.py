import asyncio

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
    def __init__(self, host: str, password: str):
        self._host = host.rstrip("/")
        self._password = password
        self._token = None

    async def _request(self, method, path, json=None):
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    async with session.request(
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

    async def login(self):
        data = await self._request(
            "POST",
            "/api/login",
            json={"password": self._password},
        )
        try:
            self._token = data["access_token"]
        except Exception as err:
            raise GreencellResponseError("Login response missing access_token") from err

    async def fetch_specification(self):
        if not self._token:
            await self.login()

        try:
            return await self._request("GET", "/api/specification")
        except GreencellAuthError:
            await self.login()
            return await self._request("GET", "/api/specification")

    async def fetch_status(self):
        if not self._token:
            await self.login()

        try:
            return await self._request("GET", "/api/current_parameters")
        except GreencellAuthError:
            await self.login()
            return await self._request("GET", "/api/current_parameters")
