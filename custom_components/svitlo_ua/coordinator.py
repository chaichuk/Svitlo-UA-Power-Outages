from __future__ import annotations

import datetime as dt
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import DtekClient
from .const import DEFAULT_SCAN_MINUTES, DOMAIN


def _merge_slots_to_intervals(off: list[bool], step_min: int) -> list[list[str]]:
    """Merge boolean slot flags into contiguous intervals."""

    def to_time(index: int) -> str:
        total = index * step_min
        return f"{total // 60:02d}:{total % 60:02d}"

    intervals: list[list[str]] = []
    start: int | None = None
    for i, value in enumerate(off):
        if value and start is None:
            start = i
        edge = (not value and start is not None) or (i == len(off) - 1 and start is not None)
        if edge and start is not None:
            end_index = i + 1 if value and i == len(off) - 1 else i
            intervals.append([to_time(start), to_time(end_index)])
            start = None
    return intervals


def _status_next(intervals: list[list[str]], now: dt.datetime) -> dict[str, Any]:
    """Determine the current or next outage status based on intervals."""
    current_minute = now.hour * 60 + now.minute

    def to_minutes(timestamp: str) -> int:
        hour, minute = map(int, timestamp.split(":"))
        return hour * 60 + minute

    for start, end in intervals:
        start_minute, end_minute = to_minutes(start), to_minutes(end)
        if start_minute <= current_minute < end_minute:
            return {"status": "off_now", "start": start, "end": end}
        if current_minute < start_minute:
            return {"status": "next_off", "start": start, "end": end}
    return {"status": "no_more_today"}


class SvitloCoordinator(DataUpdateCoordinator):
    """Coordinator that periodically fetches outage information."""

    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession, cfg: dict) -> None:
        interval = dt.timedelta(minutes=cfg.get("scan_interval_minutes", DEFAULT_SCAN_MINUTES))
        super().__init__(hass, hass.helpers.logger, name=DOMAIN, update_interval=interval)
        self._session = session
        self._cfg = cfg
        self.client = DtekClient(session)

    async def _async_update_data(self) -> dict:
        city = self._cfg["city"]
        street = self._cfg["street"]
        house = self._cfg["house"]
        update_fact = dt.datetime.now().strftime("%d.%m.%Y %H:%M")

        gpv = await self.client.fetch_queue_gpv(city, street, house, update_fact)
        if not gpv:
            raise RuntimeError("Failed to resolve GPV for address")

        html = await self.client.get_schedule_html_for_gpv(gpv)
        soup = BeautifulSoup(html, "html.parser")
        root = soup.select_one(".discon-fact-tables")
        table = root.find("table") if root else None
        row = table.select_one("tbody tr") if table else None
        intervals: list[list[str]] = []
        if row:
            cells = row.find_all("td")
            step = 30 if len(cells) >= 48 else 60

            def is_off(cell) -> bool:
                classes = cell.get("class", [])
                return any(
                    class_name in ("cell-scheduled", "cell-first-half", "cell-second-half")
                    for class_name in classes
                )

            flags = [is_off(cell) for cell in cells]
            intervals = _merge_slots_to_intervals(flags, step)

        now = dt.datetime.now()
        return {
            "address": {"city": city, "street": street, "house": house},
            "gpv": gpv,
            "today": intervals,
            "next": _status_next(intervals, now),
            "updated_at": now.isoformat(),
        }
