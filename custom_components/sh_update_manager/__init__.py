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

try:
    from homeassistant.components.frontend import async_register_built_in_panel
except ImportError:
    async_register_built_in_panel = None  # type: ignore[assignment]

try:
    from homeassistant.components.http import StaticPathConfig
except ImportError:
    StaticPathConfig = None  # type: ignore[assignment,misc]

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
    await _register_panel(hass)

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


async def _register_panel(hass: HomeAssistant) -> None:
    """Register the sidebar panel with robust fallbacks for different HA versions."""
    if DOMAIN in hass.data.get("panels_registered", set()):
        return  # Already registered

    panel_dir = os.path.join(os.path.dirname(__file__), "frontend")

    try:
        # Register static path — try new API first (HA 2024.7+), then old API
        if StaticPathConfig is not None:
            await hass.http.async_register_static_paths([
                StaticPathConfig(URL_BASE, panel_dir, cache_headers=False)
            ])
        elif hasattr(hass.http, "register_static_path"):
            hass.http.register_static_path(URL_BASE, panel_dir, cache_headers=False)
        else:
            _LOGGER.warning("Cannot register static path — unknown HA version")
            return

        # Register panel
        if async_register_built_in_panel is not None:
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
        else:
            _LOGGER.warning("async_register_built_in_panel not available")
            return

        hass.data.setdefault("panels_registered", set())
        hass.data["panels_registered"].add(DOMAIN)
        _LOGGER.info("SH Update Manager sidebar panel registered at /%s", PANEL_URL)
    except Exception:
        _LOGGER.exception("Could not register sidebar panel")


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
