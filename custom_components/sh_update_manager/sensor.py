"""Sensor entities for SH Auto Update Manager v1.2.0.

Per-queue sensors (status, pending count, items list) plus a global
overview sensor summarizing all queues.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SW_VERSION
from .queue_manager import QueueCoordinator, NamedQueue

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for each queue + global overview."""
    coordinator: QueueCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = []

    # Global overview sensor
    entities.append(GlobalOverviewSensor(entry, coordinator))

    # Per-queue sensors
    for queue in coordinator.queues:
        entities.append(QueueStatusSensor(entry, queue))
        entities.append(QueuePendingSensor(entry, queue))
        entities.append(QueueItemsSensor(entry, queue))

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
# Global overview sensor
# ---------------------------------------------------------------------------


class GlobalOverviewSensor(_DeviceInfoMixin, SensorEntity):
    """Sensor showing a summary across all queues."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:update"

    def __init__(self, entry: ConfigEntry, coordinator: QueueCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_global_overview"
        self._attr_name = "Update Manager Overview"
        self._attr_device_info = self._make_device_info(entry)

    async def async_added_to_hass(self) -> None:
        self._coordinator.register_global_listener(self._handle_update)
        for q in self._coordinator.queues:
            q.register_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.remove_global_listener(self._handle_update)
        for q in self._coordinator.queues:
            q.remove_listener(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        states = [q.state for q in self._coordinator.queues]
        if "running" in states:
            return "running"
        if "paused" in states:
            return "paused"
        return "idle"

    @property
    def extra_state_attributes(self) -> dict:
        total_pending = sum(q.pending_count for q in self._coordinator.queues)
        total_completed = sum(q.completed_count for q in self._coordinator.queues)
        total_failed = sum(q.failed_count for q in self._coordinator.queues)
        queues_summary = []
        for q in self._coordinator.queues:
            queues_summary.append({
                "name": q.name,
                "state": q.state,
                "enabled": q.enabled,
                "pending": q.pending_count,
                "completed": q.completed_count,
                "failed": q.failed_count,
            })
        return {
            "total_queues": len(self._coordinator.queues),
            "total_pending": total_pending,
            "total_completed": total_completed,
            "total_failed": total_failed,
            "queues": queues_summary,
        }


# ---------------------------------------------------------------------------
# Per-queue sensors
# ---------------------------------------------------------------------------


class _QueueSensorBase(_DeviceInfoMixin, SensorEntity):
    """Base class for per-queue sensors."""

    _attr_has_entity_name = True

    def __init__(
        self, entry: ConfigEntry, queue: NamedQueue, key: str, name_suffix: str
    ) -> None:
        self._queue = queue
        self._attr_unique_id = f"{entry.entry_id}_{queue.slug}_{key}"
        self._attr_name = f"{queue.name} {name_suffix}"
        self._attr_device_info = self._make_device_info(entry)

    async def async_added_to_hass(self) -> None:
        self._queue.register_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._queue.remove_listener(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class QueueStatusSensor(_QueueSensorBase):
    """Sensor showing the queue state (idle/running/paused/stopped)."""

    _attr_icon = "mdi:playlist-play"

    def __init__(self, entry: ConfigEntry, queue: NamedQueue) -> None:
        super().__init__(entry, queue, "status", "Status")

    @property
    def native_value(self) -> str:
        return self._queue.state

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "enabled": self._queue.enabled,
            "exec_mode": self._queue.exec_mode,
            "trigger_mode": self._queue.trigger_mode,
            "pending": self._queue.pending_count,
            "completed": self._queue.completed_count,
            "failed": self._queue.failed_count,
            "last_success": self._queue.last_success,
            "last_failure": self._queue.last_failure,
            "current_item": (
                self._queue.current_item.entity_id
                if self._queue.current_item
                else None
            ),
        }


class QueuePendingSensor(_QueueSensorBase):
    """Sensor showing the pending update count for a queue."""

    _attr_icon = "mdi:package-down"
    _attr_native_unit_of_measurement = "updates"

    def __init__(self, entry: ConfigEntry, queue: NamedQueue) -> None:
        super().__init__(entry, queue, "pending", "Pending")

    @property
    def native_value(self) -> int:
        return self._queue.pending_count


class QueueItemsSensor(_QueueSensorBase):
    """Sensor listing all items in a queue as an attribute."""

    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, entry: ConfigEntry, queue: NamedQueue) -> None:
        super().__init__(entry, queue, "items", "Items")

    @property
    def native_value(self) -> int:
        return len(self._queue.items)

    @property
    def extra_state_attributes(self) -> dict:
        return {"items": self._queue.items_summary}
