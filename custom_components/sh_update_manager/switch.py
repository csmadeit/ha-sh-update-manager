"""Switch entities for SH Auto Update Manager.

Provides auto-start toggle and pause queue toggle.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_AUTO_START, QUEUE_STATE_PAUSED, QUEUE_STATE_RUNNING
from .queue_manager import UpdateQueueManager

_LOGGER = logging.getLogger(__name__)

SW_VERSION = "1.1.0"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    queue_manager: UpdateQueueManager = hass.data[DOMAIN][entry.entry_id][
        "queue_manager"
    ]

    entities = [
        AutoStartSwitch(hass, entry, queue_manager),
        PauseQueueSwitch(entry, queue_manager),
    ]

    async_add_entities(entities)


class SHUpdateManagerSwitchBase(SwitchEntity):
    """Base class for SH Update Manager switches."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        queue_manager: UpdateQueueManager,
        key: str,
        name: str,
    ) -> None:
        self._entry = entry
        self._queue_manager = queue_manager
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SH Auto Update Manager",
            "manufacturer": "Smarter Homes LLC",
            "model": "Update Manager",
            "sw_version": SW_VERSION,
            "configuration_url": "https://smarter.homes",
        }

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self._queue_manager.register_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove update listener."""
        self._queue_manager.remove_listener(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle queue state update."""
        self.async_write_ha_state()


class AutoStartSwitch(SHUpdateManagerSwitchBase):
    """Switch to enable/disable auto-start mode.

    When enabled, the queue automatically starts processing when new
    updates are discovered during a refresh scan.
    """

    _attr_icon = "mdi:auto-download"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        queue_manager: UpdateQueueManager,
    ) -> None:
        super().__init__(
            entry, queue_manager, "auto_start", "Auto Start Queue"
        )
        self._hass = hass

    @property
    def is_on(self) -> bool:
        return self._entry.options.get(CONF_AUTO_START, False)

    async def async_turn_on(self, **kwargs) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_AUTO_START] = True
        self._hass.config_entries.async_update_entry(
            self._entry, options=new_options
        )

    async def async_turn_off(self, **kwargs) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_AUTO_START] = False
        self._hass.config_entries.async_update_entry(
            self._entry, options=new_options
        )


class PauseQueueSwitch(SHUpdateManagerSwitchBase):
    """Switch to pause/resume the queue."""

    _attr_icon = "mdi:pause-circle"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(entry, queue_manager, "pause_queue", "Pause Queue")

    @property
    def is_on(self) -> bool:
        return self._queue_manager.state == QUEUE_STATE_PAUSED

    async def async_turn_on(self, **kwargs) -> None:
        await self._queue_manager.async_pause_queue()

    async def async_turn_off(self, **kwargs) -> None:
        await self._queue_manager.async_resume_queue()
