"""Config flow for SH Auto Update Manager.

Provides a multi-step options flow with per-group execution mode settings,
Z-Wave mains-only toggle, maintenance window, and exclusion filters.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_AUTO_START,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_AREAS,
    CONF_EXCLUDE_LABELS,
    CONF_GROUP_MODES,
    CONF_ZWAVE_MAINS_ONLY,
    CONF_INSTALL_DELAY,
    CONF_INSTALL_TIMEOUT,
    CONF_MAX_RETRIES,
    CONF_MAINTENANCE_WINDOW_ENABLED,
    CONF_MAINTENANCE_WINDOW_START,
    CONF_MAINTENANCE_WINDOW_END,
    CONF_STOP_ON_FAILURE,
    CONF_SKIP_UNAVAILABLE,
    DEFAULT_INSTALL_DELAY,
    DEFAULT_INSTALL_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAINTENANCE_WINDOW_START,
    DEFAULT_MAINTENANCE_WINDOW_END,
    DEFAULT_GROUP_MODES,
    EXEC_MODES_LIST,
    GROUP_ZWAVE,
    GROUP_ESPHOME,
    GROUP_HACS,
    GROUP_HA_CORE,
    GROUP_HA_OS,
    GROUP_ADDONS,
    GROUP_MATTER,
    GROUP_MQTT,
    GROUP_OTHER,
    GROUP_DISPLAY_NAMES,
)

_LOGGER = logging.getLogger(__name__)


class SHUpdateManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for SH Auto Update Manager."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step — just creates the entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="SH Auto Update Manager",
                data={},
                options={
                    CONF_AUTO_START: False,
                    CONF_GROUP_MODES: dict(DEFAULT_GROUP_MODES),
                    CONF_ZWAVE_MAINS_ONLY: True,
                    CONF_INSTALL_DELAY: DEFAULT_INSTALL_DELAY,
                    CONF_INSTALL_TIMEOUT: DEFAULT_INSTALL_TIMEOUT,
                    CONF_MAX_RETRIES: DEFAULT_MAX_RETRIES,
                    CONF_STOP_ON_FAILURE: False,
                    CONF_SKIP_UNAVAILABLE: True,
                    CONF_MAINTENANCE_WINDOW_ENABLED: False,
                    CONF_MAINTENANCE_WINDOW_START: DEFAULT_MAINTENANCE_WINDOW_START,
                    CONF_MAINTENANCE_WINDOW_END: DEFAULT_MAINTENANCE_WINDOW_END,
                    CONF_EXCLUDE_ENTITIES: [],
                    CONF_EXCLUDE_AREAS: [],
                    CONF_EXCLUDE_LABELS: [],
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": "SH Auto Update Manager",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SHUpdateManagerOptionsFlow:
        """Get the options flow handler."""
        return SHUpdateManagerOptionsFlow(config_entry)


class SHUpdateManagerOptionsFlow(OptionsFlow):
    """Handle options flow for SH Auto Update Manager.

    Multi-step flow:
      init        -> Global settings (auto-start, delays, retries, window)
      group_modes -> Per-group execution mode selection
      filters     -> Entity/area/label exclusions
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self._options: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Global settings."""
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_group_modes()

        options = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_AUTO_START,
                        default=options.get(CONF_AUTO_START, False),
                    ): bool,
                    vol.Optional(
                        CONF_ZWAVE_MAINS_ONLY,
                        default=options.get(CONF_ZWAVE_MAINS_ONLY, True),
                    ): bool,
                    vol.Optional(
                        CONF_INSTALL_DELAY,
                        default=options.get(
                            CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=300)),
                    vol.Optional(
                        CONF_INSTALL_TIMEOUT,
                        default=options.get(
                            CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=14400)),
                    vol.Optional(
                        CONF_MAX_RETRIES,
                        default=options.get(
                            CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES
                        ),
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
                        default=options.get(
                            CONF_MAINTENANCE_WINDOW_ENABLED, False
                        ),
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
                }
            ),
        )

    async def async_step_group_modes(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Per-group execution mode selection."""
        if user_input is not None:
            # Build the group_modes dict from the flat input
            group_modes: dict[str, str] = {}
            for group_key in (
                GROUP_ZWAVE,
                GROUP_ESPHOME,
                GROUP_HACS,
                GROUP_HA_CORE,
                GROUP_HA_OS,
                GROUP_ADDONS,
                GROUP_MATTER,
                GROUP_MQTT,
                GROUP_OTHER,
            ):
                config_key = f"mode_{group_key}"
                if config_key in user_input:
                    group_modes[group_key] = user_input[config_key]
            self._options[CONF_GROUP_MODES] = group_modes
            return await self.async_step_filters()

        current_modes = self.config_entry.options.get(
            CONF_GROUP_MODES, dict(DEFAULT_GROUP_MODES)
        )

        schema_dict: dict[Any, Any] = {}
        for group_key in (
            GROUP_ZWAVE,
            GROUP_ESPHOME,
            GROUP_HACS,
            GROUP_HA_CORE,
            GROUP_HA_OS,
            GROUP_ADDONS,
            GROUP_MATTER,
            GROUP_MQTT,
            GROUP_OTHER,
        ):
            config_key = f"mode_{group_key}"
            default_mode = current_modes.get(
                group_key, DEFAULT_GROUP_MODES.get(group_key, "manual_only")
            )
            schema_dict[
                vol.Optional(config_key, default=default_mode)
            ] = vol.In(EXEC_MODES_LIST)

        return self.async_show_form(
            step_id="group_modes",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "zwave_name": GROUP_DISPLAY_NAMES[GROUP_ZWAVE],
                "esphome_name": GROUP_DISPLAY_NAMES[GROUP_ESPHOME],
                "hacs_name": GROUP_DISPLAY_NAMES[GROUP_HACS],
                "ha_core_name": GROUP_DISPLAY_NAMES[GROUP_HA_CORE],
                "ha_os_name": GROUP_DISPLAY_NAMES[GROUP_HA_OS],
                "addons_name": GROUP_DISPLAY_NAMES[GROUP_ADDONS],
                "matter_name": GROUP_DISPLAY_NAMES[GROUP_MATTER],
                "mqtt_name": GROUP_DISPLAY_NAMES[GROUP_MQTT],
                "other_name": GROUP_DISPLAY_NAMES[GROUP_OTHER],
            },
        )

    async def async_step_filters(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3: Exclusion filters."""
        if user_input is not None:
            # Parse comma-separated strings into lists
            for key in (
                CONF_EXCLUDE_ENTITIES,
                CONF_EXCLUDE_AREAS,
                CONF_EXCLUDE_LABELS,
            ):
                raw = user_input.get(key, "")
                if isinstance(raw, str):
                    self._options[key] = [
                        s.strip() for s in raw.split(",") if s.strip()
                    ]
                else:
                    self._options[key] = raw

            # Merge with any keys not explicitly in our steps
            final = dict(self.config_entry.options)
            final.update(self._options)
            return self.async_create_entry(title="", data=final)

        options = self.config_entry.options

        return self.async_show_form(
            step_id="filters",
            data_schema=vol.Schema(
                {
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
