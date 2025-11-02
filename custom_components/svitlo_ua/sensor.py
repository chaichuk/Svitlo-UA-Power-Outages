from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN

SENSORS: Sequence[tuple[str, Any]] = (
    ("Svitlo GPV", "gpv"),
    ("Svitlo Next Status", ("next", "status")),
    ("Svitlo Next Start", ("next", "start")),
    ("Svitlo Next End", ("next", "end")),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up sensors for the Svitlo integration."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [SvitloValueSensor(coordinator, name, path) for name, path in SENSORS]
    entities.append(SvitloTodaySensor(coordinator))
    async_add_entities(entities)


class SvitloBase(CoordinatorEntity):
    """Base class for Svitlo sensors with shared attributes."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DataUpdateCoordinator, name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = name

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "updated_at": data.get("updated_at"),
            "address": data.get("address"),
        }


class SvitloValueSensor(SvitloBase, SensorEntity):
    """Sensor returning scalar values from the coordinator payload."""

    def __init__(self, coordinator: DataUpdateCoordinator, name: str, path: Any) -> None:
        super().__init__(coordinator, name)
        self._path = path

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        current = data
        if isinstance(self._path, tuple):
            for key in self._path:
                current = (current or {}).get(key)
            return current
        return data.get(self._path)


class SvitloTodaySensor(SvitloBase, SensorEntity):
    """Sensor exposing information about today's planned outages."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator, "Svitlo Intervals Today")

    @property
    def native_value(self) -> int:
        data = self.coordinator.data or {}
        intervals = data.get("today") or []
        return len(intervals)

    @property
    def extra_state_attributes(self) -> dict:
        base = dict(super().extra_state_attributes)
        data = self.coordinator.data or {}
        base.update({"intervals": data.get("today")})
        return base
