"""SH Auto Update Manager — HACS integration for Home Assistant.

by Smarter Homes LLC — smarter.homes

Manages and automates update installation for all Home Assistant update
entities (Z-Wave firmware, ESPHome, HACS, etc.) with queue management,
rules, scheduling, and one-at-a-time sequential installation.
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
    PLATFORMS,
    SERVICE_START_QUEUE,
    SERVICE_PAUSE_QUEUE,
    SERVICE_RESUME_QUEUE,
    SERVICE_STOP_QUEUE,
    SERVICE_SKIP_CURRENT,
    SERVICE_REFRESH_CANDIDATES,
    SERVICE_INSTALL_ALL_ELIGIBLE,
    SERVICE_INSTALL_ENTITY,
)
from .queue_manager import UpdateQueueManager

_LOGGER = logging.getLogger(__name__)

type SHUpdateManagerConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: SHUpdateManagerConfigEntry) -> bool:
    """Set up SH Auto Update Manager from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create the queue manager with options
    queue_manager = UpdateQueueManager(hass, dict(entry.options))
    await queue_manager.async_load()

    hass.data[DOMAIN][entry.entry_id] = {
        "queue_manager": queue_manager,
    }

    # Listen for option updates
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    # Set up platforms (sensor, button, switch)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass, entry)

    _LOGGER.info("SH Auto Update Manager initialized")
    return True


async def _async_update_options(
    hass: HomeAssistant, entry: SHUpdateManagerConfigEntry
) -> None:
    """Handle options update."""
    queue_manager: UpdateQueueManager = hass.data[DOMAIN][entry.entry_id][
        "queue_manager"
    ]
    queue_manager.options = dict(entry.options)
    _LOGGER.info("Options updated")


async def async_unload_entry(
    hass: HomeAssistant, entry: SHUpdateManagerConfigEntry
) -> bool:
    """Unload a config entry."""
    queue_manager: UpdateQueueManager = hass.data[DOMAIN][entry.entry_id][
        "queue_manager"
    ]
    await queue_manager.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _get_queue_manager(hass: HomeAssistant) -> UpdateQueueManager:
    """Get the queue manager from hass data."""
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if "queue_manager" in entry_data:
            return entry_data["queue_manager"]
    raise ValueError("SH Auto Update Manager not configured")


async def _async_register_services(
    hass: HomeAssistant, entry: SHUpdateManagerConfigEntry
) -> None:
    """Register integration services."""

    async def handle_start_queue(call: ServiceCall) -> None:
        """Handle start_queue service call."""
        qm = _get_queue_manager(hass)
        await qm.async_start_queue()

    async def handle_pause_queue(call: ServiceCall) -> None:
        """Handle pause_queue service call."""
        qm = _get_queue_manager(hass)
        await qm.async_pause_queue()

    async def handle_resume_queue(call: ServiceCall) -> None:
        """Handle resume_queue service call."""
        qm = _get_queue_manager(hass)
        await qm.async_resume_queue()

    async def handle_stop_queue(call: ServiceCall) -> None:
        """Handle stop_queue service call."""
        qm = _get_queue_manager(hass)
        await qm.async_stop_queue()

    async def handle_skip_current(call: ServiceCall) -> None:
        """Handle skip_current service call."""
        qm = _get_queue_manager(hass)
        await qm.async_skip_current()

    async def handle_refresh_candidates(call: ServiceCall) -> None:
        """Handle refresh_candidates service call."""
        qm = _get_queue_manager(hass)
        await qm.async_refresh_candidates()

    async def handle_install_all_eligible(call: ServiceCall) -> None:
        """Handle install_all_eligible service call."""
        qm = _get_queue_manager(hass)
        await qm.async_install_all_eligible()

    async def handle_install_entity(call: ServiceCall) -> None:
        """Handle install_entity service call."""
        entity_id = call.data["entity_id"]
        qm = _get_queue_manager(hass)
        await qm.async_install_entity(entity_id)

    # Register all services
    hass.services.async_register(DOMAIN, SERVICE_START_QUEUE, handle_start_queue)
    hass.services.async_register(DOMAIN, SERVICE_PAUSE_QUEUE, handle_pause_queue)
    hass.services.async_register(DOMAIN, SERVICE_RESUME_QUEUE, handle_resume_queue)
    hass.services.async_register(DOMAIN, SERVICE_STOP_QUEUE, handle_stop_queue)
    hass.services.async_register(DOMAIN, SERVICE_SKIP_CURRENT, handle_skip_current)
    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH_CANDIDATES, handle_refresh_candidates
    )
    hass.services.async_register(
        DOMAIN, SERVICE_INSTALL_ALL_ELIGIBLE, handle_install_all_eligible
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_INSTALL_ENTITY,
        handle_install_entity,
        schema=vol.Schema({vol.Required("entity_id"): cv.entity_id}),
    )
