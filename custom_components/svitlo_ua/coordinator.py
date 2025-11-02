"""Координатор для оновлення даних по API."""
import aiohttp
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import const

# Часовий пояс для графіків відключень (UA)
UA_TIMEZONE = ZoneInfo("Europe/Kyiv")

class SvitloDataUpdateCoordinator(DataUpdateCoordinator):
    """Клас координації оновлення даних з Yasno/інших API."""
    def __init__(self, hass: HomeAssistant, region: str, provider: str, group: str):
        self.hass = hass
        self.region = region
        self.provider = provider  # 'yasno', 'dtek', або None для однопровайдерних регіонів
        self.group = group  # напр. '1.2' чи '4.1'
        super().__init__(hass, name=__name__, update_interval=timedelta(minutes=5))

    async def _async_update_data(self):
        """Оновлення даних повнографіку відключень."""
        data = {"events": []}
        # Визначити, яке джерело API використовувати
        region_info = const.REGION_API_MAPPING.get(self.region, {})
        api_type = region_info.get("api")
        region_code = region_info.get("region_code")

        try:
            if api_type == "yasno":
                data = await self._fetch_yasno_schedule(region_code)
            elif api_type == "energy_ua":
                data = await self._fetch_energyua_schedule(region_code)
            else:
                raise UpdateFailed(f"Unknown region or provider for {self.region}")
        except Exception as e:
            raise UpdateFailed(f"Error fetching schedule: {e}")
        return data

    async def _fetch_yasno_schedule(self, region_code: str):
        """Отримати графік відключень з Yasno API {region_code}"""
        url = "https://api.yasno.com.ua/api/v1/pages/home/schedule-turn-off-electricity"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Yasno API HTTP {resp.status}")
                result = await resp.json(content_type=None)
        # Парсимо JSON від Yasno
        components = result.get("components", [])
        schedule_comp = None
        for comp in components:
            if comp.get("template_name") == "electricity-outages-daily-schedule":
                schedule_comp = comp
                break
        if not schedule_comp:
            raise UpdateFailed("Yasno schedule component not found")
        daily = schedule_comp.get("dailySchedule", {})
        region_data = daily.get(region_code)
        if not region_data:
            raise UpdateFailed(f"Region {region_code} not in Yasno data")
        events = []
        today_info = region_data.get("today", {})
        tomorrow_info = region_data.get("tomorrow", {})
        now = datetime.now(UA_TIMEZONE)
        # Обробимо розклад на сьогодні
        events += self._parse_schedule_day(today_info, now.date())
        # Графік на завтра (якщо є)
        if tomorrow_info:
            events += self._parse_schedule_day(tomorrow_info, now.date() + timedelta(days=1))
        # Фільтруємо лише за нашою групою
        filtered_events = []
        main_group = int(self.group.split('.')[0])
        subgroup = self.group.split('.')[1] if '.' in self.group else None
        for ev in events:
            grp_key = ev.get("group_key")
            if not grp_key:
                continue
            # Беремо першу частину до "..." якщо є.
            if "..." in grp_key:
                start_range, end_range = grp_key.split("...")
                try:
                    start_range = int(start_range)
                    end_range = int(end_range)
                except:
                    continue
                if start_range <= main_group <= end_range:
                    # Додати евент, оскільки наша група в діапазоні
                    filtered_events.append(ev)
            else:
                # Точний ключ (1.1, 2.2 т.і.д.)
                if subgroup:
                    if grp_key == f"{main_group}.{subgroup}":
                        filtered_events.append(ev)
                else:
                    # Якщо задана група без підгрупи
                    try:
                        grp_main = int(grp_key.split('.')[0])
                    except:
                        grp_main = None
                    if grp_main == main_group:
                        filtered_events.append(ev)
        # Відсортуємо за часом початку
        filtered_events.sort(key=lambda x: x.get("start")) 
        return {"events": filtered_events}

    async def _fetch_energyua_schedule(self, region_code: str):
        """Отримання даних з energy-ua.info (по можливості)."""
        # Замість реального збору - повертаємо пустий набір евентів
        return {"events": []}

    def _parse_schedule_day(self, day_info: dict, base_date: datetime.date):
        """Парсинг списку інтервалів з JSON дня (сьогодні/завтра) в перелік евентів."""
        events = []
        groups = day_info.get("groups", {})
        for grp_key, intervals in groups.items():
            for interval in intervals:
                start_h = interval.get("start")
                end_h = interval.get("end")
                if start_h is None or end_h is None:
                    continue
                # Переведемо час (добовий) до дати з часом.
                start_dt = self._time_to_datetime(base_date, start_h)
                end_dt = self._time_to_datetime(base_date, end_h)
                ev_type = interval.get("type", "OUTAGE")
                events.append({
                    "start": start_dt,
                    "end": end_dt,
                    "type": ev_type,
                    "group_key": str(grp_key)
                })
        return events

    def _time_to_datetime(self, date_obj, hour_val):
        """Преведення часу в годинах (з можливим дробовим) до datetime."""
        hour = int(hour_val)
        minute = 0
        if isinstance(hour_val, float) or isinstance(hour_val, int):
            frac = hour_val - hour
            if abs(frac - 0.5) < 1e-6:
                minute = 30
        else:
            # Якщо hour_val вказано у вигляді рядку
            try:
                val = float(str(hour_val).replace(",", "."))
                hour = int(val)
                frac = val - hour
                if abs(frac - 0.5) < 1e-6:
                    minute = 30
            except:
                pass
        dt_local = datetime(year=date_obj.year, month=date_obj.month, day=date_obj.day,
                             hour=hour, minute=minute, tzinfo=UA_TIMEZONE)
        # Переводимо в UTC
        return dt_local.astimezone(dt_util.UTC)
