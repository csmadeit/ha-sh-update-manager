"""Button entities for SH Auto Update Manager.

Provides queue control buttons: update all, refresh scan, stop queue,
skip current, approve all waiting items, and clear queue.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .queue_manager import UpdateQueueManager

_LOGGER = logging.getLogger(__name__)

SW_VERSION = "1.1.0"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    queue_manager: UpdateQueueManager = hass.data[DOMAIN][entry.entry_id][
        "queue_manager"
    ]

    entities = [
        UpdateAllEligibleButton(entry, queue_manager),
        RefreshCandidatesButton(entry, queue_manager),
        StopQueueButton(entry, queue_manager),
        SkipCurrentButton(entry, queue_manager),
        ApproveAllButton(entry, queue_manager),
        ClearQueueButton(entry, queue_manager),
    ]

    async_add_entities(entities)


class SHUpdateManagerButtonBase(ButtonEntity):
    """Base class for SH Update Manager buttons."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        queue_manager: UpdateQueueManager,
        key: str,
        name: str,
    ) -> None:
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


class UpdateAllEligibleButton(SHUpdateManagerButtonBase):
    """Button to start updating all eligible entities."""

    _attr_icon = "mdi:update"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry, queue_manager, "update_all_eligible", "Update All Eligible"
        )

    async def async_press(self) -> None:
        await self._queue_manager.async_install_all_eligible()


class RefreshCandidatesButton(SHUpdateManagerButtonBase):
    """Button to refresh the list of available updates."""

    _attr_icon = "mdi:refresh"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry, queue_manager, "refresh_candidates", "Refresh Update Scan"
        )

    async def async_press(self) -> None:
        await self._queue_manager.async_refresh_candidates()


class StopQueueButton(SHUpdateManagerButtonBase):
    """Button to stop the queue."""

    _attr_icon = "mdi:stop-circle"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(entry, queue_manager, "stop_queue", "Stop Queue")

    async def async_press(self) -> None:
        await self._queue_manager.async_stop_queue()


class SkipCurrentButton(SHUpdateManagerButtonBase):
    """Button to skip the current update."""

    _attr_icon = "mdi:skip-next"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry, queue_manager, "skip_current", "Skip Current Update"
        )

    async def async_press(self) -> None:
        await self._queue_manager.async_skip_current()


class ApproveAllButton(SHUpdateManagerButtonBase):
    """Button to approve all items waiting for manual approval."""

    _attr_icon = "mdi:check-all"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry, queue_manager, "approve_all", "Approve All Waiting"
        )

    async def async_press(self) -> None:
        await self._queue_manager.async_approve_all()


class ClearQueueButton(SHUpdateManagerButtonBase):
    """Button to clear the entire queue and reset counters."""

    _attr_icon = "mdi:delete-sweep"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry, queue_manager, "clear_queue", "Clear Queue"
        )

    async def async_press(self) -> None:
        await self._queue_manager.async_clear_queue()
