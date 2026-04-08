"""Switch entities for SH Auto Update Manager v1.2.0.

Per-queue pause switches plus a global pause-all switch.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SW_VERSION, QUEUE_STATE_PAUSED, QUEUE_STATE_RUNNING
from .queue_manager import QueueCoordinator, NamedQueue

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator: QueueCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SwitchEntity] = [
        PauseAllSwitch(entry, coordinator),
    ]

    for queue in coordinator.queues:
        entities.append(PauseQueueSwitch(entry, queue, coordinator))
        entities.append(QueueEnabledSwitch(hass, entry, queue))

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
# Global switch
# ---------------------------------------------------------------------------


class PauseAllSwitch(_DeviceInfoMixin, SwitchEntity):
    """Switch to pause/resume all running queues."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:pause-circle"

    def __init__(self, entry: ConfigEntry, coordinator: QueueCoordinator) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_pause_all"
        self._attr_name = "Pause All Queues"
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
    def is_on(self) -> bool:
        return any(q.state == QUEUE_STATE_PAUSED for q in self._coordinator.queues)

    async def async_turn_on(self, **kwargs) -> None:
        for q in self._coordinator.queues:
            if q.state == QUEUE_STATE_RUNNING:
                await q.async_pause()
        await self._coordinator.async_save()

    async def async_turn_off(self, **kwargs) -> None:
        for q in self._coordinator.queues:
            if q.state == QUEUE_STATE_PAUSED:
                await q.async_resume()
        await self._coordinator.async_save()


# ---------------------------------------------------------------------------
# Per-queue switches
# ---------------------------------------------------------------------------


class PauseQueueSwitch(_DeviceInfoMixin, SwitchEntity):
    """Switch to pause/resume a specific queue."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:pause"

    def __init__(
        self, entry: ConfigEntry, queue: NamedQueue, coordinator: QueueCoordinator
    ) -> None:
        self._queue = queue
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{queue.slug}_pause"
        self._attr_name = f"Pause {queue.name}"
        self._attr_device_info = self._make_device_info(entry)

    async def async_added_to_hass(self) -> None:
        self._queue.register_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._queue.remove_listener(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._queue.state == QUEUE_STATE_PAUSED

    async def async_turn_on(self, **kwargs) -> None:
        await self._queue.async_pause()
        await self._coordinator.async_save()

    async def async_turn_off(self, **kwargs) -> None:
        await self._queue.async_resume()
        await self._coordinator.async_save()


class QueueEnabledSwitch(_DeviceInfoMixin, SwitchEntity):
    """Switch to enable/disable a queue."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:toggle-switch"

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, queue: NamedQueue
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._queue = queue
        self._attr_unique_id = f"{entry.entry_id}_{queue.slug}_enabled"
        self._attr_name = f"Enable {queue.name}"
        self._attr_device_info = self._make_device_info(entry)

    @property
    def is_on(self) -> bool:
        return self._queue.enabled

    async def async_turn_on(self, **kwargs) -> None:
        self._queue.config["enabled"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._queue.config["enabled"] = False
        self.async_write_ha_state()
