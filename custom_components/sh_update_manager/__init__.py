"""SH Auto Update Manager v2.0.2 — integration setup.

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
from homeassistant.const import Platform
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
    SW_VERSION,
)
from .queue_manager import QueueCoordinator

_LOGGER = logging.getLogger(__name__)

# Use Platform enum for forward setup
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.SWITCH]

QUEUE_SERVICE_SCHEMA = vol.Schema({
    vol.Required("queue_name"): cv.string,
})


def _hub_device_info(entry: ConfigEntry) -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "SH Update Manager",
        "manufacturer": "Smarter Homes LLC",
        "model": "Update Manager Hub",
        "sw_version": SW_VERSION,
    }


def queue_device_info(entry: ConfigEntry, queue_slug: str, queue_name: str) -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, f"{entry.entry_id}_{queue_slug}")},
        "name": f"Update Queue: {queue_name}",
        "manufacturer": "Smarter Homes LLC",
        "model": "Update Queue",
        "sw_version": SW_VERSION,
        "via_device": (DOMAIN, entry.entry_id),
    }


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to current version."""
    _LOGGER.info(
        "Migrating SH Update Manager config entry from version %s.%s to 4",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version < 4:
        # Versions 1-3 (v1.x) had completely different data schemas.
        # Reset to defaults — user can reconfigure through options flow.
        new_data = {CONF_QUEUES: list(DEFAULT_QUEUES)}
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            version=4,
            minor_version=1,
        )
        _LOGGER.info(
            "Migration complete: reset to default queues (version %s -> 4)",
            config_entry.version,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SH Auto Update Manager from a config entry."""
    _LOGGER.debug("Setting up SH Update Manager entry %s", entry.entry_id)

    # --- 1. Load queue configuration ---
    try:
        queues_config = entry.options.get(
            CONF_QUEUES, entry.data.get(CONF_QUEUES, DEFAULT_QUEUES)
        )
        if not queues_config or not isinstance(queues_config, list):
            _LOGGER.warning(
                "Invalid queues config (type=%s), falling back to defaults",
                type(queues_config).__name__,
            )
            queues_config = list(DEFAULT_QUEUES)
    except Exception:
        _LOGGER.exception("Error reading queues config, using defaults")
        queues_config = list(DEFAULT_QUEUES)

    # --- 2. Create coordinator ---
    try:
        coordinator = QueueCoordinator(hass, queues_config)
    except Exception:
        _LOGGER.exception("Error creating QueueCoordinator")
        return False

    # --- 3. Load persisted state (non-fatal) ---
    try:
        await coordinator.async_load()
    except Exception:
        _LOGGER.exception("Error loading coordinator state (continuing with fresh state)")

    # --- 4. Store in hass.data ---
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "entry": entry,
    }

    # --- 5. Register sidebar panel (non-fatal) ---
    try:
        await _register_panel(hass)
    except Exception:
        _LOGGER.exception("Panel registration failed (non-fatal, continuing)")

    # --- 6. Register services ---
    try:
        _register_services(hass, coordinator)
    except Exception:
        _LOGGER.exception("Error registering services")
        return False

    # --- 7. Forward platform setup ---
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # --- 8. Register update listener ---
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(
        "SH Update Manager v%s set up successfully with %d queue(s)",
        SW_VERSION,
        len(queues_config),
    )
    return True


def _register_services(hass: HomeAssistant, coordinator: QueueCoordinator) -> None:
    """Register all domain services."""

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


async def _register_panel(hass: HomeAssistant) -> None:
    """Register the sidebar panel with robust fallbacks for different HA versions."""
    if DOMAIN in hass.data.get("panels_registered", set()):
        _LOGGER.debug("Panel already registered, skipping")
        return

    panel_dir = os.path.join(os.path.dirname(__file__), "frontend")
    if not os.path.isdir(panel_dir):
        _LOGGER.warning("Frontend directory not found at %s", panel_dir)
        return

    panel_js = os.path.join(panel_dir, "panel.js")
    if not os.path.isfile(panel_js):
        _LOGGER.warning("panel.js not found at %s", panel_js)
        return

    try:
        # Register static path — try new API first (HA 2024.7+), then old API
        if StaticPathConfig is not None:
            await hass.http.async_register_static_paths([
                StaticPathConfig(URL_BASE, panel_dir, cache_headers=False)
            ])
        elif hasattr(hass.http, "register_static_path"):
            hass.http.register_static_path(URL_BASE, panel_dir, cache_headers=False)
        else:
            _LOGGER.warning("Cannot register static path — no compatible API found")
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
            _LOGGER.warning("async_register_built_in_panel not available — no sidebar panel")
            return

        hass.data.setdefault("panels_registered", set())
        hass.data["panels_registered"].add(DOMAIN)
        _LOGGER.info("SH Update Manager sidebar panel registered at /%s", PANEL_URL)
    except Exception:
        _LOGGER.exception("Could not register sidebar panel")


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data:
        coordinator = data.get("coordinator")
        if coordinator:
            await coordinator.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
