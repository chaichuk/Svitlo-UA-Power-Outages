from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

import aiohttp

from .const import BASE, TIMEOUT

AJAX_ENDPOINT = f"{BASE}/ua/shutdowns"


class DtekClient:
    """HTTP client for interacting with the DTEK KREM web endpoints."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _json_or_text(self, response: aiohttp.ClientResponse) -> Any:
        """Return JSON payload when possible, otherwise response text."""
        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type:
            return await response.json(content_type=None)
        return await response.text()

    async def ajax(self, data: Sequence[tuple[str, str]] | Mapping[str, str]) -> Any:
        """Perform the generic AJAX request used by the site."""
        if isinstance(data, Mapping):
            payload: Sequence[tuple[str, str]] = tuple((str(k), str(v)) for k, v in data.items())
        else:
            payload = tuple((str(k), str(v)) for k, v in data)

        async with self._session.post(AJAX_ENDPOINT, data=payload, timeout=TIMEOUT) as response:
            response.raise_for_status()
            return await self._json_or_text(response)

    async def fetch_queue_gpv(self, city: str, street: str, house: str, update_fact: str) -> str | None:
        """Resolve GPV code for the provided address."""
        data = [
            ("method", "getHomeNum"),
            ("data[0][name]", "city"),
            ("data[0][value]", city),
            ("data[1][name]", "street"),
            ("data[1][value]", street),
            ("data[2][name]", "house_num"),
            ("data[2][value]", str(house)),
            ("data[3][name]", "updateFact"),
            ("data[3][value]", update_fact),
        ]

        payload = await self.ajax(data)
        if isinstance(payload, dict):
            response_data = payload.get("data")
            if isinstance(response_data, dict) and response_data:
                first = next(iter(response_data.values()))
                sub_type_reason = (first or {}).get("sub_type_reason", [])
                if sub_type_reason:
                    return str(sub_type_reason[0])

        if isinstance(payload, str) and "GPV" in payload:
            match = re.search(r"GPV\d+(?:\.\d+)?", payload)
            if match:
                return match.group(0)
        return None

    async def fetch_house_list(self, city: str, street: str, update_fact: str) -> list[str] | None:
        """Try to retrieve a list of houses for the given address."""
        try:
            pairs = [
                ("method", "getHomeNum"),
                ("data[0][name]", "city"),
                ("data[0][value]", city),
                ("data[1][name]", "street"),
                ("data[1][value]", street),
                ("data[2][name]", "updateFact"),
                ("data[2][value]", update_fact),
            ]
            payload = await self.ajax(pairs)
        except aiohttp.ClientError:
            return None

        houses: list[str] = []
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            number = item.get("house") or item.get("number") or item.get("value")
                            if number:
                                houses.append(str(number))
        return sorted(set(houses), key=lambda x: (len(x), x)) if houses else None

    async def get_schedule_html_for_gpv(self, gpv_code: str) -> str:
        """Fetch the HTML schedule for the provided GPV code."""
        params = {"gpv": gpv_code.replace("GPV", "")}
        async with self._session.get(f"{BASE}/ua/shutdowns", params=params, timeout=TIMEOUT) as response:
            response.raise_for_status()
            return await response.text()
