"""Queue manager for SH Auto Update Manager."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers import entity_registry as er
from homeassistant.components.update import UpdateEntity
from homeassistant.const import STATE_ON

from .const import (
    DOMAIN,
    QUEUE_STATE_IDLE,
    QUEUE_STATE_PAUSED,
    QUEUE_STATE_RUNNING,
    QUEUE_STATE_STOPPED,
    CONF_INCLUDE_INTEGRATIONS,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_AREAS,
    CONF_EXCLUDE_LABELS,
    CONF_MAINS_POWERED_ONLY,
    CONF_ONE_AT_A_TIME,
    CONF_INSTALL_DELAY,
    CONF_INSTALL_TIMEOUT,
    CONF_MAX_RETRIES,
    CONF_MAINTENANCE_WINDOW_ENABLED,
    CONF_MAINTENANCE_WINDOW_START,
    CONF_MAINTENANCE_WINDOW_END,
    CONF_STOP_ON_FAILURE,
    CONF_SKIP_UNAVAILABLE,
    CONF_CATEGORY_FILTER,
    CATEGORY_ALL,
    DEFAULT_INSTALL_DELAY,
    DEFAULT_INSTALL_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class QueueItem:
    """Represents a single update in the queue."""

    def __init__(self, entity_id: str) -> None:
        """Initialize a queue item."""
        self.entity_id = entity_id
        self.retries = 0
        self.status = "pending"  # pending, installing, completed, failed, skipped
        self.error: str | None = None
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "entity_id": self.entity_id,
            "retries": self.retries,
            "status": self.status,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueueItem:
        """Deserialize from dict."""
        item = cls(data["entity_id"])
        item.retries = data.get("retries", 0)
        item.status = data.get("status", "pending")
        item.error = data.get("error")
        if data.get("started_at"):
            item.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            item.completed_at = datetime.fromisoformat(data["completed_at"])
        return item


class UpdateQueueManager:
    """Manages the sequential update queue."""

    def __init__(self, hass: HomeAssistant, options: dict[str, Any]) -> None:
        """Initialize the queue manager."""
        self.hass = hass
        self.options = options
        self._queue: list[QueueItem] = []
        self._state = QUEUE_STATE_IDLE
        self._current_item: QueueItem | None = None
        self._task: asyncio.Task | None = None
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._last_success: str | None = None
        self._last_failure: str | None = None
        self._completed_count = 0
        self._failed_count = 0
        self._listeners: list[Any] = []

    @property
    def state(self) -> str:
        """Return the current queue state."""
        return self._state

    @property
    def current_item(self) -> QueueItem | None:
        """Return the currently installing item."""
        return self._current_item

    @property
    def queue(self) -> list[QueueItem]:
        """Return the current queue."""
        return self._queue

    @property
    def pending_count(self) -> int:
        """Return the number of pending updates."""
        return len([i for i in self._queue if i.status == "pending"])

    @property
    def completed_count(self) -> int:
        """Return the number of completed updates this session."""
        return self._completed_count

    @property
    def failed_count(self) -> int:
        """Return the number of failed updates this session."""
        return self._failed_count

    @property
    def last_success(self) -> str | None:
        """Return the last successfully updated entity."""
        return self._last_success

    @property
    def last_failure(self) -> str | None:
        """Return the last failed entity."""
        return self._last_failure

    def register_listener(self, listener: Any) -> None:
        """Register a state change listener."""
        self._listeners.append(listener)

    def remove_listener(self, listener: Any) -> None:
        """Remove a state change listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    @callback
    def _notify_listeners(self) -> None:
        """Notify all listeners of state change."""
        for listener in self._listeners:
            listener()

    async def async_load(self) -> None:
        """Load persisted queue state."""
        data = await self._store.async_load()
        if data and "queue" in data:
            self._queue = [QueueItem.from_dict(item) for item in data["queue"]]
            self._state = data.get("state", QUEUE_STATE_IDLE)
            self._last_success = data.get("last_success")
            self._last_failure = data.get("last_failure")
            self._completed_count = data.get("completed_count", 0)
            self._failed_count = data.get("failed_count", 0)
            _LOGGER.info(
                "Loaded persisted queue: %d items, state=%s",
                len(self._queue),
                self._state,
            )

    async def async_save(self) -> None:
        """Persist queue state."""
        data = {
            "queue": [item.to_dict() for item in self._queue],
            "state": self._state,
            "last_success": self._last_success,
            "last_failure": self._last_failure,
            "completed_count": self._completed_count,
            "failed_count": self._failed_count,
        }
        await self._store.async_save(data)

    def _is_in_maintenance_window(self) -> bool:
        """Check if current time is within the maintenance window."""
        if not self.options.get(CONF_MAINTENANCE_WINDOW_ENABLED, False):
            return True  # No window restriction

        now = datetime.now().time()
        start_str = self.options.get(CONF_MAINTENANCE_WINDOW_START, "02:00")
        end_str = self.options.get(CONF_MAINTENANCE_WINDOW_END, "05:00")

        start = time.fromisoformat(start_str)
        end = time.fromisoformat(end_str)

        if start <= end:
            return start <= now <= end
        # Crosses midnight
        return now >= start or now <= end

    async def async_discover_updates(self) -> list[str]:
        """Discover all available update entities with updates pending."""
        ent_reg = er.async_get(self.hass)
        update_entities: list[str] = []

        include_integrations = self.options.get(CONF_INCLUDE_INTEGRATIONS, [])
        exclude_entities = self.options.get(CONF_EXCLUDE_ENTITIES, [])
        exclude_areas = self.options.get(CONF_EXCLUDE_AREAS, [])
        exclude_labels = self.options.get(CONF_EXCLUDE_LABELS, [])
        category_filter = self.options.get(CONF_CATEGORY_FILTER, CATEGORY_ALL)

        for entity_entry in ent_reg.entities.values():
            # Only update entities
            if not entity_entry.entity_id.startswith("update."):
                continue

            # Check if entity is disabled
            if entity_entry.disabled:
                continue

            # Check exclusions
            if entity_entry.entity_id in exclude_entities:
                continue

            # Check area exclusion
            if exclude_areas and entity_entry.area_id in exclude_areas:
                continue

            # Check label exclusion
            if exclude_labels and hasattr(entity_entry, "labels"):
                if entity_entry.labels and entity_entry.labels.intersection(
                    set(exclude_labels)
                ):
                    continue

            # Check integration filter
            if include_integrations:
                if entity_entry.platform not in include_integrations:
                    continue

            # Check state — only entities with available updates (state = "on")
            state = self.hass.states.get(entity_entry.entity_id)
            if state is None or state.state != STATE_ON:
                continue

            # Check category filter
            if category_filter != CATEGORY_ALL and state.attributes:
                device_class = state.attributes.get("device_class", "")
                if category_filter == "firmware" and device_class != "firmware":
                    continue

            # Check if unavailable and skip_unavailable is set
            if self.options.get(CONF_SKIP_UNAVAILABLE, True):
                if state.state == "unavailable":
                    continue

            update_entities.append(entity_entry.entity_id)

        _LOGGER.info("Discovered %d eligible update entities", len(update_entities))
        return update_entities

    async def async_refresh_candidates(self) -> int:
        """Refresh the list of update candidates and rebuild the queue."""
        entities = await self.async_discover_updates()

        # Only add entities not already in queue
        existing_ids = {item.entity_id for item in self._queue}
        new_count = 0
        for entity_id in entities:
            if entity_id not in existing_ids:
                self._queue.append(QueueItem(entity_id))
                new_count += 1

        # Remove completed/failed items that no longer have updates
        self._queue = [
            item
            for item in self._queue
            if item.entity_id in entities or item.status == "installing"
        ]

        await self.async_save()
        self._notify_listeners()
        _LOGGER.info(
            "Refreshed candidates: %d total, %d new", len(self._queue), new_count
        )
        return len(self._queue)

    async def async_start_queue(self) -> None:
        """Start processing the update queue."""
        if self._state == QUEUE_STATE_RUNNING:
            _LOGGER.warning("Queue is already running")
            return

        await self.async_refresh_candidates()

        if not self._queue:
            _LOGGER.info("No updates available to install")
            return

        self._state = QUEUE_STATE_RUNNING
        self._notify_listeners()
        await self.async_save()

        # Start the processing loop
        self._task = self.hass.async_create_task(self._async_process_queue())

    async def async_pause_queue(self) -> None:
        """Pause the queue processing."""
        if self._state != QUEUE_STATE_RUNNING:
            return
        self._state = QUEUE_STATE_PAUSED
        self._notify_listeners()
        await self.async_save()
        _LOGGER.info("Queue paused")

    async def async_resume_queue(self) -> None:
        """Resume the queue processing."""
        if self._state != QUEUE_STATE_PAUSED:
            return
        self._state = QUEUE_STATE_RUNNING
        self._notify_listeners()
        await self.async_save()
        _LOGGER.info("Queue resumed")

    async def async_stop_queue(self) -> None:
        """Stop the queue processing."""
        self._state = QUEUE_STATE_STOPPED
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._current_item = None
        self._notify_listeners()
        await self.async_save()
        _LOGGER.info("Queue stopped")

    async def async_skip_current(self) -> None:
        """Skip the currently installing update."""
        if self._current_item:
            self._current_item.status = "skipped"
            self._current_item.completed_at = datetime.now()
            _LOGGER.info("Skipping current update: %s", self._current_item.entity_id)
            self._current_item = None
            self._notify_listeners()

    async def async_install_entity(self, entity_id: str) -> None:
        """Install a specific entity update immediately."""
        _LOGGER.info("Manual install requested for: %s", entity_id)
        await self._async_install_single(entity_id)

    async def async_install_all_eligible(self) -> None:
        """Start installing all eligible updates."""
        await self.async_start_queue()

    async def _async_process_queue(self) -> None:
        """Process the update queue sequentially."""
        _LOGGER.info("Starting queue processing with %d items", len(self._queue))

        while self._queue:
            # Check if stopped
            if self._state == QUEUE_STATE_STOPPED:
                break

            # Check if paused — wait until resumed
            while self._state == QUEUE_STATE_PAUSED:
                await asyncio.sleep(5)
                if self._state == QUEUE_STATE_STOPPED:
                    return

            # Check maintenance window
            if not self._is_in_maintenance_window():
                _LOGGER.info("Outside maintenance window, waiting...")
                await asyncio.sleep(60)
                continue

            # Find next pending item
            next_item = None
            for item in self._queue:
                if item.status == "pending":
                    next_item = item
                    break

            if next_item is None:
                break

            # Install it
            self._current_item = next_item
            self._notify_listeners()

            success = await self._async_install_single(next_item.entity_id)

            if success:
                next_item.status = "completed"
                next_item.completed_at = datetime.now()
                self._last_success = next_item.entity_id
                self._completed_count += 1
                _LOGGER.info("Successfully updated: %s", next_item.entity_id)
            else:
                max_retries = self.options.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES)
                next_item.retries += 1
                if next_item.retries >= max_retries:
                    next_item.status = "failed"
                    next_item.completed_at = datetime.now()
                    self._last_failure = next_item.entity_id
                    self._failed_count += 1
                    _LOGGER.error(
                        "Update failed after %d retries: %s",
                        next_item.retries,
                        next_item.entity_id,
                    )

                    if self.options.get(CONF_STOP_ON_FAILURE, False):
                        _LOGGER.info("Stopping queue due to failure (stop_on_failure)")
                        self._state = QUEUE_STATE_STOPPED
                        break
                else:
                    next_item.status = "pending"  # Will retry
                    _LOGGER.warning(
                        "Update failed, will retry (%d/%d): %s",
                        next_item.retries,
                        max_retries,
                        next_item.entity_id,
                    )

            self._current_item = None
            self._notify_listeners()
            await self.async_save()

            # Delay between installs
            delay = self.options.get(CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY)
            if delay > 0 and self._state == QUEUE_STATE_RUNNING:
                _LOGGER.debug("Waiting %d seconds before next install", delay)
                await asyncio.sleep(delay)

        # Done processing
        if self._state == QUEUE_STATE_RUNNING:
            self._state = QUEUE_STATE_IDLE
        self._current_item = None
        self._notify_listeners()
        await self.async_save()
        _LOGGER.info(
            "Queue processing complete. Completed: %d, Failed: %d",
            self._completed_count,
            self._failed_count,
        )

    async def _async_install_single(self, entity_id: str) -> bool:
        """Install a single update entity and wait for completion."""
        _LOGGER.info("Installing update: %s", entity_id)

        # Verify the entity still has an update available
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning("Entity not found: %s", entity_id)
            return False

        if state.state != STATE_ON:
            _LOGGER.info("Entity no longer has update available: %s", entity_id)
            return True  # Consider it done

        try:
            # Call update.install
            await self.hass.services.async_call(
                "update",
                "install",
                {"entity_id": entity_id},
                blocking=False,
            )
        except Exception as err:
            _LOGGER.error("Failed to call update.install for %s: %s", entity_id, err)
            return False

        # Wait for the update to complete
        timeout = self.options.get(CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT)
        elapsed = 0
        poll_interval = 10  # Check every 10 seconds

        while elapsed < timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            # Check if we were stopped/paused
            if self._state == QUEUE_STATE_STOPPED:
                return False

            state = self.hass.states.get(entity_id)
            if state is None:
                _LOGGER.warning("Entity disappeared during update: %s", entity_id)
                return False

            # Check if in_progress
            in_progress = state.attributes.get("in_progress")
            if in_progress is True or (
                isinstance(in_progress, (int, float)) and in_progress > 0
            ):
                _LOGGER.debug(
                    "Update in progress for %s (elapsed: %ds)", entity_id, elapsed
                )
                continue

            # Check if the update is no longer available (state went to "off")
            if state.state != STATE_ON:
                _LOGGER.info("Update completed for %s", entity_id)
                return True

            # If in_progress is False/None and state is still "on", might be stalled
            if in_progress is False or in_progress is None:
                # Give it a bit more time in case it just hasn't started yet
                if elapsed > 60:
                    _LOGGER.warning(
                        "Update appears stalled for %s (not in_progress, still on)",
                        entity_id,
                    )
                    return False

        _LOGGER.error("Update timed out after %ds for %s", timeout, entity_id)
        return False

    async def async_shutdown(self) -> None:
        """Shut down the queue manager."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.async_save()
