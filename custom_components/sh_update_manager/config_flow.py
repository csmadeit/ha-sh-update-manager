"""Config flow for SH Auto Update Manager."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_INCLUDE_INTEGRATIONS,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_AREAS,
    CONF_EXCLUDE_LABELS,
    CONF_AUTO_UPDATE,
    CONF_MAINS_POWERED_ONLY,
    CONF_ONE_AT_A_TIME,
    CONF_INSTALL_DELAY,
    CONF_INSTALL_TIMEOUT,
    CONF_MAX_RETRIES,
    CONF_MAINTENANCE_WINDOW_ENABLED,
    CONF_MAINTENANCE_WINDOW_START,
    CONF_MAINTENANCE_WINDOW_END,
    CONF_STOP_ON_FAILURE,
    CONF_SKIP_UNAVAILABLE,
    CONF_CATEGORY_FILTER,
    CATEGORY_ALL,
    DEFAULT_INSTALL_DELAY,
    DEFAULT_INSTALL_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAINTENANCE_WINDOW_START,
    DEFAULT_MAINTENANCE_WINDOW_END,
)

_LOGGER = logging.getLogger(__name__)


class SHUpdateManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for SH Auto Update Manager."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        # Only allow a single instance
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="SH Auto Update Manager",
                data={},
                options={
                    CONF_AUTO_UPDATE: user_input.get(CONF_AUTO_UPDATE, False),
                    CONF_ONE_AT_A_TIME: True,
                    CONF_MAINS_POWERED_ONLY: user_input.get(
                        CONF_MAINS_POWERED_ONLY, False
                    ),
                    CONF_CATEGORY_FILTER: user_input.get(
                        CONF_CATEGORY_FILTER, CATEGORY_ALL
                    ),
                    CONF_INSTALL_DELAY: DEFAULT_INSTALL_DELAY,
                    CONF_INSTALL_TIMEOUT: DEFAULT_INSTALL_TIMEOUT,
                    CONF_MAX_RETRIES: DEFAULT_MAX_RETRIES,
                    CONF_STOP_ON_FAILURE: False,
                    CONF_SKIP_UNAVAILABLE: True,
                    CONF_MAINTENANCE_WINDOW_ENABLED: False,
                    CONF_MAINTENANCE_WINDOW_START: DEFAULT_MAINTENANCE_WINDOW_START,
                    CONF_MAINTENANCE_WINDOW_END: DEFAULT_MAINTENANCE_WINDOW_END,
                    CONF_INCLUDE_INTEGRATIONS: [],
                    CONF_EXCLUDE_ENTITIES: [],
                    CONF_EXCLUDE_AREAS: [],
                    CONF_EXCLUDE_LABELS: [],
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_AUTO_UPDATE, default=False): bool,
                    vol.Optional(CONF_MAINS_POWERED_ONLY, default=False): bool,
                    vol.Optional(
                        CONF_CATEGORY_FILTER, default=CATEGORY_ALL
                    ): vol.In(["all", "firmware"]),
                }
            ),
            description_placeholders={
                "name": "SH Auto Update Manager",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SHUpdateManagerOptionsFlow:
        """Get the options flow handler."""
        return SHUpdateManagerOptionsFlow(config_entry)


class SHUpdateManagerOptionsFlow(OptionsFlow):
    """Handle options flow for SH Auto Update Manager."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the main options step."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_AUTO_UPDATE,
                        default=options.get(CONF_AUTO_UPDATE, False),
                    ): bool,
                    vol.Optional(
                        CONF_MAINS_POWERED_ONLY,
                        default=options.get(CONF_MAINS_POWERED_ONLY, False),
                    ): bool,
                    vol.Optional(
                        CONF_ONE_AT_A_TIME,
                        default=options.get(CONF_ONE_AT_A_TIME, True),
                    ): bool,
                    vol.Optional(
                        CONF_CATEGORY_FILTER,
                        default=options.get(CONF_CATEGORY_FILTER, CATEGORY_ALL),
                    ): vol.In(["all", "firmware"]),
                    vol.Optional(
                        CONF_INSTALL_DELAY,
                        default=options.get(CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=300)),
                    vol.Optional(
                        CONF_INSTALL_TIMEOUT,
                        default=options.get(
                            CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=14400)),
                    vol.Optional(
                        CONF_MAX_RETRIES,
                        default=options.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=10)),
                    vol.Optional(
                        CONF_STOP_ON_FAILURE,
                        default=options.get(CONF_STOP_ON_FAILURE, False),
                    ): bool,
                    vol.Optional(
                        CONF_SKIP_UNAVAILABLE,
                        default=options.get(CONF_SKIP_UNAVAILABLE, True),
                    ): bool,
                    vol.Optional(
                        CONF_MAINTENANCE_WINDOW_ENABLED,
                        default=options.get(CONF_MAINTENANCE_WINDOW_ENABLED, False),
                    ): bool,
                    vol.Optional(
                        CONF_MAINTENANCE_WINDOW_START,
                        default=options.get(
                            CONF_MAINTENANCE_WINDOW_START,
                            DEFAULT_MAINTENANCE_WINDOW_START,
                        ),
                    ): str,
                    vol.Optional(
                        CONF_MAINTENANCE_WINDOW_END,
                        default=options.get(
                            CONF_MAINTENANCE_WINDOW_END,
                            DEFAULT_MAINTENANCE_WINDOW_END,
                        ),
                    ): str,
                    vol.Optional(
                        CONF_INCLUDE_INTEGRATIONS,
                        default=",".join(
                            options.get(CONF_INCLUDE_INTEGRATIONS, [])
                        ),
                    ): str,
                    vol.Optional(
                        CONF_EXCLUDE_ENTITIES,
                        default=",".join(
                            options.get(CONF_EXCLUDE_ENTITIES, [])
                        ),
                    ): str,
                    vol.Optional(
                        CONF_EXCLUDE_AREAS,
                        default=",".join(
                            options.get(CONF_EXCLUDE_AREAS, [])
                        ),
                    ): str,
                    vol.Optional(
                        CONF_EXCLUDE_LABELS,
                        default=",".join(
                            options.get(CONF_EXCLUDE_LABELS, [])
                        ),
                    ): str,
                }
            ),
        )
