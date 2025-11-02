from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up binary sensors for the Svitlo integration."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([SvitloOffNow(coordinator)])


class SvitloOffNow(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that indicates whether power is currently off."""

    _attr_has_entity_name = True
    _attr_name = "Svitlo Off Now"

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return (data.get("next") or {}).get("status") == "off_now"

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "updated_at": data.get("updated_at"),
            "address": data.get("address"),
            "gpv": data.get("gpv"),
            "today": data.get("today"),
        }
