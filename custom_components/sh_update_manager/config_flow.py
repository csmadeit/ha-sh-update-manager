"""Config flow for SH Auto Update Manager v1.2.0.

Queue-based architecture: users create named queues with independent
match rules, execution modes, and trigger settings.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import copy
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_QUEUES,
    CONF_QUEUE_NAME,
    CONF_MATCH_TYPE,
    CONF_MATCH_VALUE,
    CONF_EXEC_MODE,
    CONF_TRIGGER_MODE,
    CONF_ZWAVE_MAINS_ONLY,
    CONF_STOP_ON_FAILURE,
    CONF_SKIP_UNAVAILABLE,
    CONF_INSTALL_DELAY,
    CONF_INSTALL_TIMEOUT,
    CONF_MAX_RETRIES,
    CONF_QUEUE_ENABLED,
    DEFAULT_QUEUES,
    DEFAULT_INSTALL_DELAY,
    DEFAULT_INSTALL_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    EXEC_MODES_LIST,
    TRIGGER_MODES_LIST,
    MATCH_TYPES_LIST,
    TRIGGER_MANUAL,
    EXEC_MODE_SEQUENTIAL,
    MATCH_INTEGRATION,
)

_LOGGER = logging.getLogger(__name__)


class SHUpdateManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow — creates entry with default queues."""

    VERSION = 3

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="SH Auto Update Manager",
                data={},
                options={CONF_QUEUES: copy.deepcopy(DEFAULT_QUEUES)},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={"name": "SH Auto Update Manager"},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SHUpdateManagerOptionsFlow:
        """Get the options flow handler."""
        return SHUpdateManagerOptionsFlow(config_entry)


class SHUpdateManagerOptionsFlow(OptionsFlow):
    """Options flow: list queues, add/edit/remove queues.

    Steps:
      init         -> Show list of queues with add/edit/remove actions
      add_queue    -> Create a new queue (name + match rule)
      edit_queue   -> Edit an existing queue's settings
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self._queues: list[dict[str, Any]] = []
        self._editing_index: int | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Show queue list and actions."""
        self._queues = copy.deepcopy(
            self.config_entry.options.get(CONF_QUEUES, DEFAULT_QUEUES)
        )

        if user_input is not None:
            action = user_input.get("action", "done")
            if action == "add":
                return await self.async_step_add_queue()
            if action.startswith("edit_"):
                try:
                    self._editing_index = int(action.split("_", 1)[1])
                    return await self.async_step_edit_queue()
                except (ValueError, IndexError):
                    pass
            if action.startswith("remove_"):
                try:
                    idx = int(action.split("_", 1)[1])
                    if 0 <= idx < len(self._queues):
                        self._queues.pop(idx)
                        return self.async_create_entry(
                            title="", data={CONF_QUEUES: self._queues}
                        )
                except (ValueError, IndexError):
                    pass
            # "done" or fallback
            return self.async_create_entry(
                title="", data={CONF_QUEUES: self._queues}
            )

        # Build action options
        actions = {}
        for i, q in enumerate(self._queues):
            name = q.get("name", f"Queue {i}")
            enabled = q.get(CONF_QUEUE_ENABLED, True)
            status = "ON" if enabled else "OFF"
            actions[f"edit_{i}"] = f"Edit: {name} [{status}]"
            actions[f"remove_{i}"] = f"Remove: {name}"
        actions["add"] = "Add new queue"
        actions["done"] = "Done (save changes)"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="done"): vol.In(actions),
                }
            ),
        )

    async def async_step_add_queue(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new queue."""
        if user_input is not None:
            new_queue = {
                CONF_QUEUE_NAME: user_input[CONF_QUEUE_NAME],
                CONF_MATCH_TYPE: user_input.get(CONF_MATCH_TYPE, MATCH_INTEGRATION),
                CONF_MATCH_VALUE: user_input.get(CONF_MATCH_VALUE, ""),
                CONF_EXEC_MODE: user_input.get(CONF_EXEC_MODE, EXEC_MODE_SEQUENTIAL),
                CONF_TRIGGER_MODE: user_input.get(CONF_TRIGGER_MODE, TRIGGER_MANUAL),
                CONF_ZWAVE_MAINS_ONLY: user_input.get(CONF_ZWAVE_MAINS_ONLY, False),
                CONF_STOP_ON_FAILURE: user_input.get(CONF_STOP_ON_FAILURE, False),
                CONF_SKIP_UNAVAILABLE: user_input.get(CONF_SKIP_UNAVAILABLE, True),
                CONF_INSTALL_DELAY: user_input.get(CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY),
                CONF_INSTALL_TIMEOUT: user_input.get(CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT),
                CONF_MAX_RETRIES: user_input.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES),
                CONF_QUEUE_ENABLED: user_input.get(CONF_QUEUE_ENABLED, True),
            }
            self._queues.append(new_queue)
            return self.async_create_entry(
                title="", data={CONF_QUEUES: self._queues}
            )

        return self.async_show_form(
            step_id="add_queue",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_QUEUE_NAME): str,
                    vol.Required(CONF_MATCH_TYPE, default=MATCH_INTEGRATION): vol.In(
                        MATCH_TYPES_LIST
                    ),
                    vol.Required(CONF_MATCH_VALUE, default=""): str,
                    vol.Required(CONF_EXEC_MODE, default=EXEC_MODE_SEQUENTIAL): vol.In(
                        EXEC_MODES_LIST
                    ),
                    vol.Required(CONF_TRIGGER_MODE, default=TRIGGER_MANUAL): vol.In(
                        TRIGGER_MODES_LIST
                    ),
                    vol.Optional(CONF_ZWAVE_MAINS_ONLY, default=False): bool,
                    vol.Optional(CONF_STOP_ON_FAILURE, default=False): bool,
                    vol.Optional(CONF_SKIP_UNAVAILABLE, default=True): bool,
                    vol.Optional(
                        CONF_INSTALL_DELAY, default=DEFAULT_INSTALL_DELAY
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=300)),
                    vol.Optional(
                        CONF_INSTALL_TIMEOUT, default=DEFAULT_INSTALL_TIMEOUT
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=14400)),
                    vol.Optional(
                        CONF_MAX_RETRIES, default=DEFAULT_MAX_RETRIES
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=10)),
                    vol.Optional(CONF_QUEUE_ENABLED, default=True): bool,
                }
            ),
        )

    async def async_step_edit_queue(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit an existing queue."""
        if self._editing_index is None or self._editing_index >= len(self._queues):
            return await self.async_step_init()

        queue = self._queues[self._editing_index]

        if user_input is not None:
            queue[CONF_QUEUE_NAME] = user_input.get(
                CONF_QUEUE_NAME, queue.get("name", "")
            )
            queue[CONF_MATCH_TYPE] = user_input.get(
                CONF_MATCH_TYPE, queue.get(CONF_MATCH_TYPE, MATCH_INTEGRATION)
            )
            queue[CONF_MATCH_VALUE] = user_input.get(
                CONF_MATCH_VALUE, queue.get(CONF_MATCH_VALUE, "")
            )
            queue[CONF_EXEC_MODE] = user_input.get(
                CONF_EXEC_MODE, queue.get(CONF_EXEC_MODE, EXEC_MODE_SEQUENTIAL)
            )
            queue[CONF_TRIGGER_MODE] = user_input.get(
                CONF_TRIGGER_MODE, queue.get(CONF_TRIGGER_MODE, TRIGGER_MANUAL)
            )
            queue[CONF_ZWAVE_MAINS_ONLY] = user_input.get(CONF_ZWAVE_MAINS_ONLY, False)
            queue[CONF_STOP_ON_FAILURE] = user_input.get(CONF_STOP_ON_FAILURE, False)
            queue[CONF_SKIP_UNAVAILABLE] = user_input.get(CONF_SKIP_UNAVAILABLE, True)
            queue[CONF_INSTALL_DELAY] = user_input.get(
                CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY
            )
            queue[CONF_INSTALL_TIMEOUT] = user_input.get(
                CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT
            )
            queue[CONF_MAX_RETRIES] = user_input.get(
                CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES
            )
            queue[CONF_QUEUE_ENABLED] = user_input.get(CONF_QUEUE_ENABLED, True)
            self._queues[self._editing_index] = queue
            return self.async_create_entry(
                title="", data={CONF_QUEUES: self._queues}
            )

        return self.async_show_form(
            step_id="edit_queue",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_QUEUE_NAME, default=queue.get("name", "")
                    ): str,
                    vol.Required(
                        CONF_MATCH_TYPE,
                        default=queue.get(CONF_MATCH_TYPE, MATCH_INTEGRATION),
                    ): vol.In(MATCH_TYPES_LIST),
                    vol.Required(
                        CONF_MATCH_VALUE,
                        default=queue.get(CONF_MATCH_VALUE, ""),
                    ): str,
                    vol.Required(
                        CONF_EXEC_MODE,
                        default=queue.get(CONF_EXEC_MODE, EXEC_MODE_SEQUENTIAL),
                    ): vol.In(EXEC_MODES_LIST),
                    vol.Required(
                        CONF_TRIGGER_MODE,
                        default=queue.get(CONF_TRIGGER_MODE, TRIGGER_MANUAL),
                    ): vol.In(TRIGGER_MODES_LIST),
                    vol.Optional(
                        CONF_ZWAVE_MAINS_ONLY,
                        default=queue.get(CONF_ZWAVE_MAINS_ONLY, False),
                    ): bool,
                    vol.Optional(
                        CONF_STOP_ON_FAILURE,
                        default=queue.get(CONF_STOP_ON_FAILURE, False),
                    ): bool,
                    vol.Optional(
                        CONF_SKIP_UNAVAILABLE,
                        default=queue.get(CONF_SKIP_UNAVAILABLE, True),
                    ): bool,
                    vol.Optional(
                        CONF_INSTALL_DELAY,
                        default=queue.get(CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=300)),
                    vol.Optional(
                        CONF_INSTALL_TIMEOUT,
                        default=queue.get(CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=14400)),
                    vol.Optional(
                        CONF_MAX_RETRIES,
                        default=queue.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=10)),
                    vol.Optional(
                        CONF_QUEUE_ENABLED,
                        default=queue.get(CONF_QUEUE_ENABLED, True),
                    ): bool,
                }
            ),
        )
