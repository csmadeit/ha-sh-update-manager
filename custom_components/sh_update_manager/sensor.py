"""Sensor entities for SH Auto Update Manager.

Provides queue status, pending count, current target, last success/failure,
completed/failed counts, waiting-for-approval count, and full queue list
as a sensor attribute for dashboard display.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
    """Set up sensor entities."""
    queue_manager: UpdateQueueManager = hass.data[DOMAIN][entry.entry_id][
        "queue_manager"
    ]

    entities = [
        QueueStatusSensor(entry, queue_manager),
        PendingUpdatesSensor(entry, queue_manager),
        WaitingApprovalSensor(entry, queue_manager),
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


class QueueStatusSensor(SHUpdateManagerSensorBase):
    """Sensor showing the current queue status with full queue list."""

    _attr_icon = "mdi:update"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(entry, queue_manager, "queue_status", "Queue Status")

    @property
    def native_value(self) -> str:
        return self._queue_manager.state

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes including the full queue list."""
        queue = self._queue_manager.queue
        return {
            "total_in_queue": len(queue),
            "pending": self._queue_manager.pending_count,
            "waiting_approval": self._queue_manager.waiting_approval_count,
            "installing": len([i for i in queue if i.status == "installing"]),
            "completed": len([i for i in queue if i.status == "completed"]),
            "failed": len([i for i in queue if i.status == "failed"]),
            "skipped": len([i for i in queue if i.status == "skipped"]),
            "queue_items": self._queue_manager.queue_summary,
        }


class PendingUpdatesSensor(SHUpdateManagerSensorBase):
    """Sensor showing the number of pending updates."""

    _attr_icon = "mdi:package-down"
    _attr_native_unit_of_measurement = "updates"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry, queue_manager, "pending_updates", "Pending Updates"
        )

    @property
    def native_value(self) -> int:
        return self._queue_manager.pending_count


class WaitingApprovalSensor(SHUpdateManagerSensorBase):
    """Sensor showing the number of items waiting for manual approval."""

    _attr_icon = "mdi:account-check"
    _attr_native_unit_of_measurement = "updates"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry,
            queue_manager,
            "waiting_approval",
            "Waiting Approval",
        )

    @property
    def native_value(self) -> int:
        return self._queue_manager.waiting_approval_count

    @property
    def extra_state_attributes(self) -> dict:
        """List items waiting for approval."""
        return {
            "items": [
                {
                    "entity_id": i.entity_id,
                    "group": i.group,
                    "friendly_name": i.friendly_name,
                    "latest_version": i.latest_version,
                }
                for i in self._queue_manager.queue
                if i.status == "waiting_approval"
            ]
        }


class CurrentUpdateSensor(SHUpdateManagerSensorBase):
    """Sensor showing the currently updating entity."""

    _attr_icon = "mdi:progress-download"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry, queue_manager, "current_update", "Current Update Target"
        )

    @property
    def native_value(self) -> str | None:
        item = self._queue_manager.current_item
        return item.entity_id if item else None

    @property
    def extra_state_attributes(self) -> dict:
        item = self._queue_manager.current_item
        if item:
            return {
                "group": item.group,
                "friendly_name": item.friendly_name,
                "installed_version": item.installed_version,
                "latest_version": item.latest_version,
                "retries": item.retries,
            }
        return {}


class LastSuccessSensor(SHUpdateManagerSensorBase):
    """Sensor showing the last successfully updated entity."""

    _attr_icon = "mdi:check-circle"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(entry, queue_manager, "last_success", "Last Success")

    @property
    def native_value(self) -> str | None:
        return self._queue_manager.last_success


class LastFailureSensor(SHUpdateManagerSensorBase):
    """Sensor showing the last failed entity."""

    _attr_icon = "mdi:alert-circle"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(entry, queue_manager, "last_failure", "Last Failure")

    @property
    def native_value(self) -> str | None:
        return self._queue_manager.last_failure


class CompletedCountSensor(SHUpdateManagerSensorBase):
    """Sensor showing the completed update count."""

    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = "updates"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry, queue_manager, "completed_count", "Completed Updates"
        )

    @property
    def native_value(self) -> int:
        return self._queue_manager.completed_count


class FailedCountSensor(SHUpdateManagerSensorBase):
    """Sensor showing the failed update count."""

    _attr_icon = "mdi:alert-octagon"
    _attr_native_unit_of_measurement = "updates"

    def __init__(
        self, entry: ConfigEntry, queue_manager: UpdateQueueManager
    ) -> None:
        super().__init__(
            entry, queue_manager, "failed_count", "Failed Updates"
        )

    @property
    def native_value(self) -> int:
        return self._queue_manager.failed_count
