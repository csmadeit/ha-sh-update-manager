"""Button entities for SH Auto Update Manager v1.2.0.

Per-queue buttons (start, stop, skip) plus global buttons
(scan all, start all, stop all).

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SW_VERSION
from .queue_manager import QueueCoordinator, NamedQueue

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    coordinator: QueueCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[ButtonEntity] = [
        ScanAllButton(entry, coordinator),
        StartAllButton(entry, coordinator),
        StopAllButton(entry, coordinator),
    ]

    for queue in coordinator.queues:
        entities.append(StartQueueButton(entry, queue, coordinator))
        entities.append(StopQueueButton(entry, queue, coordinator))
        entities.append(SkipCurrentButton(entry, queue, coordinator))

    async_add_entities(entities)


class _DeviceInfoMixin:
    """Mixin to provide consistent device info."""

    def _make_device_info(self, entry: ConfigEntry) -> dict:
        return {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SH Auto Update Manager",
            "manufacturer": "Smarter Homes LLC",
            "model": "Update Manager",
            "sw_version": SW_VERSION,
            "configuration_url": "https://smarter.homes",
        }


# ---------------------------------------------------------------------------
# Global buttons
# ---------------------------------------------------------------------------


class ScanAllButton(_DeviceInfoMixin, ButtonEntity):
    """Button to scan all queues for new updates."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:refresh"

    def __init__(self, entry: ConfigEntry, coordinator: QueueCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_scan_all"
        self._attr_name = "Scan All Queues"
        self._attr_device_info = self._make_device_info(entry)

    async def async_press(self) -> None:
        await self._coordinator.async_scan_all()


class StartAllButton(_DeviceInfoMixin, ButtonEntity):
    """Button to start all enabled queues."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:play-circle"

    def __init__(self, entry: ConfigEntry, coordinator: QueueCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_start_all"
        self._attr_name = "Start All Queues"
        self._attr_device_info = self._make_device_info(entry)

    async def async_press(self) -> None:
        await self._coordinator.async_start_all()


class StopAllButton(_DeviceInfoMixin, ButtonEntity):
    """Button to stop all running queues."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:stop-circle"

    def __init__(self, entry: ConfigEntry, coordinator: QueueCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_stop_all"
        self._attr_name = "Stop All Queues"
        self._attr_device_info = self._make_device_info(entry)

    async def async_press(self) -> None:
        await self._coordinator.async_stop_all()


# ---------------------------------------------------------------------------
# Per-queue buttons
# ---------------------------------------------------------------------------


class StartQueueButton(_DeviceInfoMixin, ButtonEntity):
    """Button to start a specific queue."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:play"

    def __init__(
        self, entry: ConfigEntry, queue: NamedQueue, coordinator: QueueCoordinator
    ) -> None:
        self._queue = queue
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{queue.slug}_start"
        self._attr_name = f"Start {queue.name}"
        self._attr_device_info = self._make_device_info(entry)

    async def async_press(self) -> None:
        await self._queue.async_start()
        await self._coordinator.async_save()


class StopQueueButton(_DeviceInfoMixin, ButtonEntity):
    """Button to stop a specific queue."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:stop"

    def __init__(
        self, entry: ConfigEntry, queue: NamedQueue, coordinator: QueueCoordinator
    ) -> None:
        self._queue = queue
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{queue.slug}_stop"
        self._attr_name = f"Stop {queue.name}"
        self._attr_device_info = self._make_device_info(entry)

    async def async_press(self) -> None:
        await self._queue.async_stop()
        await self._coordinator.async_save()


class SkipCurrentButton(_DeviceInfoMixin, ButtonEntity):
    """Button to skip the current item in a queue."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:skip-next"

    def __init__(
        self, entry: ConfigEntry, queue: NamedQueue, coordinator: QueueCoordinator
    ) -> None:
        self._queue = queue
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{queue.slug}_skip"
        self._attr_name = f"Skip Current in {queue.name}"
        self._attr_device_info = self._make_device_info(entry)

    async def async_press(self) -> None:
        await self._queue.async_skip_current()
        await self._coordinator.async_save()
