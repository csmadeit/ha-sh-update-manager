"""SH Auto Update Manager v1.2.0 — HACS integration for Home Assistant.

by Smarter Homes LLC — smarter.homes

Queue-based architecture: multiple named queues with independent match
rules, execution modes, and trigger settings.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_QUEUES,
    DEFAULT_QUEUES,
    PLATFORMS,
    SW_VERSION,
    SERVICE_SCAN_ALL,
    SERVICE_START_ALL,
    SERVICE_STOP_ALL,
    SERVICE_START_QUEUE,
    SERVICE_STOP_QUEUE,
    SERVICE_PAUSE_QUEUE,
    SERVICE_RESUME_QUEUE,
    SERVICE_SKIP_CURRENT,
    SERVICE_CLEAR_QUEUE,
)
from .queue_manager import QueueCoordinator

_LOGGER = logging.getLogger(__name__)

type SHUpdateManagerConfigEntry = ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: SHUpdateManagerConfigEntry
) -> bool:
    """Set up SH Auto Update Manager from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    queues_config = entry.options.get(CONF_QUEUES, DEFAULT_QUEUES)
    coordinator = QueueCoordinator(hass, queues_config)
    await coordinator.async_load()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await _async_register_services(hass)

    _LOGGER.info("SH Auto Update Manager v%s initialized", SW_VERSION)
    return True


async def _async_update_options(
    hass: HomeAssistant, entry: SHUpdateManagerConfigEntry
) -> None:
    """Handle options update — reload the entry to pick up queue changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: SHUpdateManagerConfigEntry
) -> bool:
    """Unload a config entry."""
    coordinator: QueueCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _get_coordinator(hass: HomeAssistant) -> QueueCoordinator:
    """Get the queue coordinator from hass data."""
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_data, dict) and "coordinator" in entry_data:
            return entry_data["coordinator"]
    raise ValueError("SH Auto Update Manager not configured")


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""

    async def handle_scan_all(call: ServiceCall) -> None:
        coord = _get_coordinator(hass)
        await coord.async_scan_all()

    async def handle_start_all(call: ServiceCall) -> None:
        coord = _get_coordinator(hass)
        await coord.async_start_all()

    async def handle_stop_all(call: ServiceCall) -> None:
        coord = _get_coordinator(hass)
        await coord.async_stop_all()

    async def handle_start_queue(call: ServiceCall) -> None:
        queue_name = call.data["queue_name"]
        coord = _get_coordinator(hass)
        queue = coord.get_queue(queue_name)
        if queue:
            await queue.async_start()
            await coord.async_save()

    async def handle_stop_queue(call: ServiceCall) -> None:
        queue_name = call.data["queue_name"]
        coord = _get_coordinator(hass)
        queue = coord.get_queue(queue_name)
        if queue:
            await queue.async_stop()
            await coord.async_save()

    async def handle_pause_queue(call: ServiceCall) -> None:
        queue_name = call.data["queue_name"]
        coord = _get_coordinator(hass)
        queue = coord.get_queue(queue_name)
        if queue:
            await queue.async_pause()
            await coord.async_save()

    async def handle_resume_queue(call: ServiceCall) -> None:
        queue_name = call.data["queue_name"]
        coord = _get_coordinator(hass)
        queue = coord.get_queue(queue_name)
        if queue:
            await queue.async_resume()
            await coord.async_save()

    async def handle_skip_current(call: ServiceCall) -> None:
        queue_name = call.data["queue_name"]
        coord = _get_coordinator(hass)
        queue = coord.get_queue(queue_name)
        if queue:
            await queue.async_skip_current()
            await coord.async_save()

    async def handle_clear_queue(call: ServiceCall) -> None:
        queue_name = call.data["queue_name"]
        coord = _get_coordinator(hass)
        queue = coord.get_queue(queue_name)
        if queue:
            await queue.async_clear()
            await coord.async_save()

    queue_name_schema = vol.Schema({vol.Required("queue_name"): cv.string})

    if not hass.services.has_service(DOMAIN, SERVICE_SCAN_ALL):
        hass.services.async_register(DOMAIN, SERVICE_SCAN_ALL, handle_scan_all)
        hass.services.async_register(DOMAIN, SERVICE_START_ALL, handle_start_all)
        hass.services.async_register(DOMAIN, SERVICE_STOP_ALL, handle_stop_all)
        hass.services.async_register(
            DOMAIN, SERVICE_START_QUEUE, handle_start_queue, schema=queue_name_schema
        )
        hass.services.async_register(
            DOMAIN, SERVICE_STOP_QUEUE, handle_stop_queue, schema=queue_name_schema
        )
        hass.services.async_register(
            DOMAIN, SERVICE_PAUSE_QUEUE, handle_pause_queue, schema=queue_name_schema
        )
        hass.services.async_register(
            DOMAIN, SERVICE_RESUME_QUEUE, handle_resume_queue, schema=queue_name_schema
        )
        hass.services.async_register(
            DOMAIN, SERVICE_SKIP_CURRENT, handle_skip_current, schema=queue_name_schema
        )
        hass.services.async_register(
            DOMAIN, SERVICE_CLEAR_QUEUE, handle_clear_queue, schema=queue_name_schema
        )
