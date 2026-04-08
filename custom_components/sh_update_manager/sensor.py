"""Sensor entities for SH Auto Update Manager."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .queue_manager import UpdateQueueManager

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    queue_manager: UpdateQueueManager = hass.data[DOMAIN][entry.entry_id][
        "queue_manager"
    ]

    entities = [
        QueueStatusSensor(entry, queue_manager),
        PendingUpdatesSensor(entry, queue_manager),
        CurrentUpdateSensor(entry, queue_manager),
        LastSuccessSensor(entry, queue_manager),
        LastFailureSensor(entry, queue_manager),
        CompletedCountSensor(entry, queue_manager),
        FailedCountSensor(entry, queue_manager),
    ]

    async_add_entities(entities)


class SHUpdateManagerSensorBase(SensorEntity):
    """Base class for SH Update Manager sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        queue_manager: UpdateQueueManager,
        key: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        self._queue_manager = queue_manager
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SH Auto Update Manager",
            "manufacturer": "Smarter Homes LLC",
            "model": "Update Manager",
            "sw_version": "1.0.0",
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


class QueueStatusSensor(SHUpdateManagerSensorBase):
    """Sensor showing the current queue status."""

    _attr_icon = "mdi:update"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        """Initialize."""
        super().__init__(entry, queue_manager, "queue_status", "Queue Status")

    @property
    def native_value(self) -> str:
        """Return the queue state."""
        return self._queue_manager.state

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        queue = self._queue_manager.queue
        return {
            "total_in_queue": len(queue),
            "pending": len([i for i in queue if i.status == "pending"]),
            "installing": len([i for i in queue if i.status == "installing"]),
            "completed": len([i for i in queue if i.status == "completed"]),
            "failed": len([i for i in queue if i.status == "failed"]),
            "skipped": len([i for i in queue if i.status == "skipped"]),
        }


class PendingUpdatesSensor(SHUpdateManagerSensorBase):
    """Sensor showing the number of pending updates."""

    _attr_icon = "mdi:package-down"
    _attr_native_unit_of_measurement = "updates"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        """Initialize."""
        super().__init__(entry, queue_manager, "pending_updates", "Pending Updates")

    @property
    def native_value(self) -> int:
        """Return the pending count."""
        return self._queue_manager.pending_count


class CurrentUpdateSensor(SHUpdateManagerSensorBase):
    """Sensor showing the currently updating entity."""

    _attr_icon = "mdi:progress-download"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        """Initialize."""
        super().__init__(
            entry, queue_manager, "current_update", "Current Update Target"
        )

    @property
    def native_value(self) -> str | None:
        """Return the current entity being updated."""
        item = self._queue_manager.current_item
        return item.entity_id if item else None


class LastSuccessSensor(SHUpdateManagerSensorBase):
    """Sensor showing the last successfully updated entity."""

    _attr_icon = "mdi:check-circle"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        """Initialize."""
        super().__init__(entry, queue_manager, "last_success", "Last Success")

    @property
    def native_value(self) -> str | None:
        """Return the last success."""
        return self._queue_manager.last_success


class LastFailureSensor(SHUpdateManagerSensorBase):
    """Sensor showing the last failed entity."""

    _attr_icon = "mdi:alert-circle"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        """Initialize."""
        super().__init__(entry, queue_manager, "last_failure", "Last Failure")

    @property
    def native_value(self) -> str | None:
        """Return the last failure."""
        return self._queue_manager.last_failure


class CompletedCountSensor(SHUpdateManagerSensorBase):
    """Sensor showing the completed update count."""

    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = "updates"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        """Initialize."""
        super().__init__(
            entry, queue_manager, "completed_count", "Completed Updates"
        )

    @property
    def native_value(self) -> int:
        """Return the completed count."""
        return self._queue_manager.completed_count


class FailedCountSensor(SHUpdateManagerSensorBase):
    """Sensor showing the failed update count."""

    _attr_icon = "mdi:alert-octagon"
    _attr_native_unit_of_measurement = "updates"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        """Initialize."""
        super().__init__(entry, queue_manager, "failed_count", "Failed Updates")

    @property
    def native_value(self) -> int:
        """Return the failed count."""
        return self._queue_manager.failed_count
