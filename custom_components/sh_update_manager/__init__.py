"""SH Auto Update Manager v2.0.0 — integration setup.

Device-per-queue architecture: each queue registers as a separate HA device.
A hub device provides global overview and controls.
Sidebar panel for queue management UI.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.components.frontend import (
    async_register_built_in_panel,
)
from homeassistant.components.http import StaticPathConfig

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_QUEUES,
    SERVICE_SCAN_ALL,
    SERVICE_START_QUEUE,
    SERVICE_STOP_QUEUE,
    SERVICE_PAUSE_QUEUE,
    SERVICE_RESUME_QUEUE,
    SERVICE_SKIP_CURRENT,
    SERVICE_CLEAR_QUEUE,
    SERVICE_RETRY_FAILED,
    SERVICE_SCAN_QUEUE,
    DEFAULT_QUEUES,
    PANEL_URL,
    PANEL_TITLE,
    PANEL_ICON,
    URL_BASE,
)
from .queue_manager import QueueCoordinator

_LOGGER = logging.getLogger(__name__)

QUEUE_SERVICE_SCHEMA = vol.Schema({
    vol.Required("queue_name"): cv.string,
})


def _hub_device_info(entry: ConfigEntry) -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "SH Update Manager",
        "manufacturer": "Smarter Homes LLC",
        "model": "Update Manager Hub",
        "sw_version": "2.0.0",
        "entry_type": "service",
    }


def queue_device_info(entry: ConfigEntry, queue_slug: str, queue_name: str) -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, f"{entry.entry_id}_{queue_slug}")},
        "name": f"Update Queue: {queue_name}",
        "manufacturer": "Smarter Homes LLC",
        "model": "Update Queue",
        "sw_version": "2.0.0",
        "via_device": (DOMAIN, entry.entry_id),
    }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    queues_config = entry.options.get(CONF_QUEUES, entry.data.get(CONF_QUEUES, DEFAULT_QUEUES))
    coordinator = QueueCoordinator(hass, queues_config)
    await coordinator.async_load()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "entry": entry,
    }

    # Register sidebar panel
    try:
        panel_dir = os.path.join(os.path.dirname(__file__), "frontend")
        await hass.http.async_register_static_paths([
            StaticPathConfig(URL_BASE, panel_dir, cache_headers=False)
        ])
        async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL,
            config={
                "_panel_custom": {
                    "name": "sh-update-manager-panel",
                    "module_url": f"{URL_BASE}/panel.js",
                }
            },
            require_admin=False,
        )
    except Exception:
        _LOGGER.warning("Could not register sidebar panel — frontend may not be available")

    # Register services
    async def handle_scan_all(call: ServiceCall) -> None:
        await coordinator.async_scan_all()
        await coordinator.async_save()

    async def handle_start_queue(call: ServiceCall) -> None:
        q = coordinator.get_queue(call.data["queue_name"])
        if q:
            await q.async_start()
            await coordinator.async_save()

    async def handle_stop_queue(call: ServiceCall) -> None:
        q = coordinator.get_queue(call.data["queue_name"])
        if q:
            await q.async_stop()
            await coordinator.async_save()

    async def handle_pause_queue(call: ServiceCall) -> None:
        q = coordinator.get_queue(call.data["queue_name"])
        if q:
            await q.async_pause()

    async def handle_resume_queue(call: ServiceCall) -> None:
        q = coordinator.get_queue(call.data["queue_name"])
        if q:
            await q.async_resume()

    async def handle_skip_current(call: ServiceCall) -> None:
        q = coordinator.get_queue(call.data["queue_name"])
        if q:
            await q.async_skip_current()

    async def handle_clear_queue(call: ServiceCall) -> None:
        q = coordinator.get_queue(call.data["queue_name"])
        if q:
            await q.async_clear()
            await coordinator.async_save()

    async def handle_retry_failed(call: ServiceCall) -> None:
        q = coordinator.get_queue(call.data["queue_name"])
        if q:
            await q.async_retry_failed()
            await coordinator.async_save()

    async def handle_scan_queue(call: ServiceCall) -> None:
        q = coordinator.get_queue(call.data["queue_name"])
        if q:
            await q.async_scan()
            await coordinator.async_save()

    hass.services.async_register(DOMAIN, SERVICE_SCAN_ALL, handle_scan_all)
    hass.services.async_register(DOMAIN, SERVICE_START_QUEUE, handle_start_queue, schema=QUEUE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STOP_QUEUE, handle_stop_queue, schema=QUEUE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PAUSE_QUEUE, handle_pause_queue, schema=QUEUE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_RESUME_QUEUE, handle_resume_queue, schema=QUEUE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SKIP_CURRENT, handle_skip_current, schema=QUEUE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_QUEUE, handle_clear_queue, schema=QUEUE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_RETRY_FAILED, handle_retry_failed, schema=QUEUE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SCAN_QUEUE, handle_scan_queue, schema=QUEUE_SERVICE_SCHEMA)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data:
        coordinator = data["coordinator"]
        await coordinator.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
