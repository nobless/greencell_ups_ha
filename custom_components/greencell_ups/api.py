import aiohttp
import async_timeout

class GreencellApi:
    def __init__(self, host: str, password: str):
        self._host = host.rstrip("/")
        self._password = password
        self._token = None

    async def _request(self, method, path, json=None):
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(10):
                async with session.request(
                    method,
                    f"{self._host}{path}",
                    json=json,
                    headers=headers,
                ) as resp:
                    if resp.status == 401:
                        self._token = None
                        raise PermissionError
                    resp.raise_for_status()
                    return await resp.json()

    async def login(self):
        data = await self._request(
            "POST",
            "/api/login",
            json={"password": self._password},
        )
        self._token = data["access_token"]

    async def fetch_status(self):
        if not self._token:
            await self.login()

        try:
            return await self._request("GET", "/api/current_parameters")
        except PermissionError:
            await self.login()
            return await self._request("GET", "/api/current_parameters")
