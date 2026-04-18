"""Config flow for Smarter.Homes Update Manager v2.0.0.

Setup: queue selection with proper names and descriptions.
Options: full queue CRUD — add/edit/delete with battery options, priority.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import copy
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    SW_VERSION,
    DEFAULT_QUEUES,
    CONF_QUEUES,
    CONF_QUEUE_NAME,
    CONF_MATCH_TYPE,
    CONF_MATCH_VALUE,
    CONF_EXEC_MODE,
    CONF_TRIGGER_MODE,
    CONF_BATTERY_HANDLING,
    CONF_STOP_ON_FAILURE,
    CONF_SKIP_UNAVAILABLE,
    CONF_INSTALL_DELAY,
    CONF_INSTALL_TIMEOUT,
    CONF_MAX_RETRIES,
    CONF_HISTORY_COUNT,
    CONF_PRIORITY,
    CONF_SCAN_INTERVAL_MINUTES,
    EXEC_MODES_LIST,
    TRIGGER_MODES_LIST,
    BATTERY_MODES_LIST,
    MATCH_TYPES_LIST,
    BATTERY_EXCLUDE,
    BATTERY_DEFER_TO_END,
    BATTERY_INCLUDE,
    DEFAULT_INSTALL_DELAY,
    DEFAULT_INSTALL_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_HISTORY_COUNT,
    DEFAULT_PRIORITY,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    GROUP_DISPLAY_NAMES,
)


class SHUpdateManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 6

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            selected = []
            for i, q in enumerate(DEFAULT_QUEUES):
                if user_input.get(f"queue_{i}", False):
                    selected.append(copy.deepcopy(q))
            if not selected:
                selected = [copy.deepcopy(DEFAULT_QUEUES[0])]
            return self.async_create_entry(
                title="Smarter.Homes Update Manager",
                data={CONF_QUEUES: selected},
            )

        schema_dict = {}
        for i, q in enumerate(DEFAULT_QUEUES):
            schema_dict[vol.Optional(f"queue_{i}", default=True)] = bool
        schema_dict[vol.Optional("queue_info", default="")] = str

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "queue_info": "Select which default queues to create. You can add more later in options.",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return SHUpdateManagerOptionsFlow(config_entry)


class SHUpdateManagerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._queues: list[dict[str, Any]] = list(
            config_entry.options.get(CONF_QUEUES, config_entry.data.get(CONF_QUEUES, []))
        )
        self._scan_interval: int = int(
            config_entry.options.get(
                CONF_SCAN_INTERVAL_MINUTES,
                config_entry.data.get(
                    CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
                ),
            )
        )
        self._editing_index: int | None = None

    def _save_entry(self) -> FlowResult:
        return self.async_create_entry(
            title="Smarter.Homes Update Manager",
            data={
                CONF_QUEUES: self._queues,
                CONF_SCAN_INTERVAL_MINUTES: self._scan_interval,
            },
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            action = user_input.get("action", "done")
            if action == "add":
                return await self.async_step_add_queue()
            if action == "global_settings":
                return await self.async_step_global_settings()
            if action.startswith("edit_"):
                idx = int(action.split("_")[1])
                self._editing_index = idx
                return await self.async_step_edit_queue()
            if action.startswith("delete_"):
                idx = int(action.split("_")[1])
                if 0 <= idx < len(self._queues):
                    self._queues.pop(idx)
                return await self.async_step_init()
            # done
            return self._save_entry()

        options = {
            "global_settings": (
                f"Global settings (auto-scan: "
                f"{self._scan_interval} min{'s' if self._scan_interval != 1 else ''}"
                f"{' — off' if self._scan_interval == 0 else ''})"
            ),
            "add": "Add new queue",
            "done": "Save and close",
        }
        for i, q in enumerate(self._queues):
            options[f"edit_{i}"] = f"Edit: {q.get(CONF_QUEUE_NAME, f'Queue {i}')}"
            options[f"delete_{i}"] = f"Delete: {q.get(CONF_QUEUE_NAME, f'Queue {i}')}"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("action", default="done"): vol.In(options),
            }),
        )

    async def async_step_global_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._scan_interval = int(
                user_input.get(
                    CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
                )
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id="global_settings",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL_MINUTES,
                    default=self._scan_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=10080)),
            }),
        )

    async def async_step_add_queue(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            new_queue = {
                CONF_QUEUE_NAME: user_input[CONF_QUEUE_NAME],
                CONF_MATCH_TYPE: user_input[CONF_MATCH_TYPE],
                CONF_MATCH_VALUE: user_input[CONF_MATCH_VALUE],
                CONF_EXEC_MODE: user_input[CONF_EXEC_MODE],
                CONF_TRIGGER_MODE: user_input[CONF_TRIGGER_MODE],
                CONF_BATTERY_HANDLING: user_input[CONF_BATTERY_HANDLING],
                CONF_STOP_ON_FAILURE: user_input.get(CONF_STOP_ON_FAILURE, False),
                CONF_SKIP_UNAVAILABLE: user_input.get(CONF_SKIP_UNAVAILABLE, True),
                CONF_INSTALL_DELAY: user_input.get(CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY),
                CONF_INSTALL_TIMEOUT: user_input.get(CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT),
                CONF_MAX_RETRIES: user_input.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES),
                CONF_HISTORY_COUNT: user_input.get(CONF_HISTORY_COUNT, DEFAULT_HISTORY_COUNT),
                CONF_PRIORITY: user_input.get(CONF_PRIORITY, DEFAULT_PRIORITY),
            }
            self._queues.append(new_queue)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="add_queue",
            data_schema=vol.Schema({
                vol.Required(CONF_QUEUE_NAME): str,
                vol.Required(CONF_MATCH_TYPE, default="integration"): vol.In(MATCH_TYPES_LIST),
                vol.Required(CONF_MATCH_VALUE): str,
                vol.Required(CONF_EXEC_MODE, default="sequential"): vol.In(EXEC_MODES_LIST),
                vol.Required(CONF_TRIGGER_MODE, default="manual"): vol.In(TRIGGER_MODES_LIST),
                vol.Required(CONF_BATTERY_HANDLING, default=BATTERY_EXCLUDE): vol.In(BATTERY_MODES_LIST),
                vol.Optional(CONF_STOP_ON_FAILURE, default=False): bool,
                vol.Optional(CONF_SKIP_UNAVAILABLE, default=True): bool,
                vol.Optional(CONF_INSTALL_DELAY, default=DEFAULT_INSTALL_DELAY): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=300)
                ),
                vol.Optional(CONF_INSTALL_TIMEOUT, default=DEFAULT_INSTALL_TIMEOUT): vol.All(
                    vol.Coerce(int), vol.Range(min=60, max=14400)
                ),
                vol.Optional(CONF_MAX_RETRIES, default=DEFAULT_MAX_RETRIES): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=10)
                ),
                vol.Optional(CONF_HISTORY_COUNT, default=DEFAULT_HISTORY_COUNT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=100)
                ),
                vol.Optional(CONF_PRIORITY, default=DEFAULT_PRIORITY): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=100)
                ),
            }),
        )

    async def async_step_edit_queue(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        idx = self._editing_index
        if idx is None or idx >= len(self._queues):
            return await self.async_step_init()

        current = self._queues[idx]

        if user_input is not None:
            current.update({
                CONF_QUEUE_NAME: user_input[CONF_QUEUE_NAME],
                CONF_MATCH_TYPE: user_input[CONF_MATCH_TYPE],
                CONF_MATCH_VALUE: user_input[CONF_MATCH_VALUE],
                CONF_EXEC_MODE: user_input[CONF_EXEC_MODE],
                CONF_TRIGGER_MODE: user_input[CONF_TRIGGER_MODE],
                CONF_BATTERY_HANDLING: user_input[CONF_BATTERY_HANDLING],
                CONF_STOP_ON_FAILURE: user_input.get(CONF_STOP_ON_FAILURE, False),
                CONF_SKIP_UNAVAILABLE: user_input.get(CONF_SKIP_UNAVAILABLE, True),
                CONF_INSTALL_DELAY: user_input.get(CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY),
                CONF_INSTALL_TIMEOUT: user_input.get(CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT),
                CONF_MAX_RETRIES: user_input.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES),
                CONF_HISTORY_COUNT: user_input.get(CONF_HISTORY_COUNT, DEFAULT_HISTORY_COUNT),
                CONF_PRIORITY: user_input.get(CONF_PRIORITY, DEFAULT_PRIORITY),
            })
            self._editing_index = None
            return await self.async_step_init()

        return self.async_show_form(
            step_id="edit_queue",
            data_schema=vol.Schema({
                vol.Required(CONF_QUEUE_NAME, default=current.get(CONF_QUEUE_NAME, "")): str,
                vol.Required(CONF_MATCH_TYPE, default=current.get(CONF_MATCH_TYPE, "integration")): vol.In(MATCH_TYPES_LIST),
                vol.Required(CONF_MATCH_VALUE, default=current.get(CONF_MATCH_VALUE, "")): str,
                vol.Required(CONF_EXEC_MODE, default=current.get(CONF_EXEC_MODE, "sequential")): vol.In(EXEC_MODES_LIST),
                vol.Required(CONF_TRIGGER_MODE, default=current.get(CONF_TRIGGER_MODE, "manual")): vol.In(TRIGGER_MODES_LIST),
                vol.Required(CONF_BATTERY_HANDLING, default=current.get(CONF_BATTERY_HANDLING, BATTERY_EXCLUDE)): vol.In(BATTERY_MODES_LIST),
                vol.Optional(CONF_STOP_ON_FAILURE, default=current.get(CONF_STOP_ON_FAILURE, False)): bool,
                vol.Optional(CONF_SKIP_UNAVAILABLE, default=current.get(CONF_SKIP_UNAVAILABLE, True)): bool,
                vol.Optional(CONF_INSTALL_DELAY, default=current.get(CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY)): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=300)
                ),
                vol.Optional(CONF_INSTALL_TIMEOUT, default=current.get(CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT)): vol.All(
                    vol.Coerce(int), vol.Range(min=60, max=14400)
                ),
                vol.Optional(CONF_MAX_RETRIES, default=current.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES)): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=10)
                ),
                vol.Optional(CONF_HISTORY_COUNT, default=current.get(CONF_HISTORY_COUNT, DEFAULT_HISTORY_COUNT)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=100)
                ),
                vol.Optional(CONF_PRIORITY, default=current.get(CONF_PRIORITY, DEFAULT_PRIORITY)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=100)
                ),
            }),
        )
