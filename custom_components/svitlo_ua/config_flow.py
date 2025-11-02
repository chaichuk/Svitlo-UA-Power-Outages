"""Конфігураційний потік (UI) для інтеграції 'Світло'."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from . import const

_LOGGER = logging.getLogger(__name__)

class SvitloConfigFlow(config_entries.ConfigFlow, domain=const.DOMAIN):
    """Клас налаштування інтеграції через UI."""
    VERSION = 1

    def __init__(self):
        self._region = None
        self._provider = None

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            self._region = user_input["region"]
            # Перевірка: чи вже конфігуровано цей регіон+групу
            existing = [entry for entry in self._async_current_entries() if entry.data.get("region") == self._region]
            if existing:
                return self.async_abort(reason="already_configured")
            # якщо в обраному регіоні дві можливі компанії:
            if self._region == "Київ":
                return await self.async_step_provider()
            else:
                return await self.async_step_group()
        # Список можливих регіонів для вибору
        regions = list(const.REGION_API_MAPPING.keys())
        data_schema = vol.Schema({
            vol.Required("region"): vol.In(regions)
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_provider(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            self._provider = user_input["provider"]
            return await self.async_step_group()
        # Для Києва дві опції постачальника
        options = ["Yasno (м.\u00a0Київ)", "ДТЕК Київські електромережі"]
        data_schema = vol.Schema({
            vol.Required("provider"): vol.In(options)
        })
        return self.async_show_form(step_id="provider", data_schema=data_schema, errors=errors)

    async def async_step_group(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            group = user_input["group"]
            # Перевірка на дублювання:
            for entry in self._async_current_entries():
                if entry.data.get("region") == self._region and entry.data.get("group") == group:
                    return self.async_abort(reason="already_configured")
            # Створити config entry
            provider_code = None
            if self._provider is not None:
                if self._provider.startswith("Yasno"):
                    provider_code = "yasno"
                elif self._provider.startswith("ДТЕК"):
                    provider_code = "dtek"
            data = {"region": self._region, "provider": provider_code, "group": group}
            return self.async_create_entry(title=f"Світло - {self._region} {group}", data=data)
        # Отримання списку груп для регіону
        # Наразі - 1.1-6.2 за замовчуванням
        group_options = [f"{i}.{j}" for i in range(1, 7) for j in (1, 2)]
        data_schema = vol.Schema({
            vol.Required("group"): vol.In(group_options)
        })
        return self.async_show_form(step_id="group", data_schema=data_schema, errors=errors)
