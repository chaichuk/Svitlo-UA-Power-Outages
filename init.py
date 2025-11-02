"""Init module for Svitlo UA Power Outages integration."""
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PLATFORMS
from .coordinator import SvitloUADataUpdateCoordinator

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration via YAML (not used, only UI)."""
    # Налаштування через YAML не підтримується (тільки через UI)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Svitlo UA integration from a config entry."""
    # Ініціалізація координатора оновлення даних
    hass.data.setdefault(DOMAIN, {})
    coordinator = SvitloUADataUpdateCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()  # Перший запит даних

    # Зберігаємо координатор у загальному сховищі
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Реєструємо платформи (сенсори, binary_sensor, календар)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Вивантажуємо платформи та видаляємо дані
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
