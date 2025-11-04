from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import DOMAIN, PLATFORMS, CONF_REGION, CONF_QUEUE, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import SvitloCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Підняти інтеграцію з ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})

    # Збираємо конфіг для координатора: region, queue, scan_interval
    config = {
        CONF_REGION: entry.data[CONF_REGION],
        CONF_QUEUE: entry.data[CONF_QUEUE],
        CONF_SCAN_INTERVAL: entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    }

    coordinator = SvitloCoordinator(hass, config)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Форвардимо налаштування платформ
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Вивантажити інтеграцію (прибрати платформи та координатор)."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
