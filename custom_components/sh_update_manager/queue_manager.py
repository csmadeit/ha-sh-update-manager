"""Queue manager for SH Auto Update Manager.

Handles discovery, grouping, filtering, and sequential/parallel installation
of Home Assistant update entities with per-group execution modes.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers import entity_registry as er
from homeassistant.const import STATE_ON

from .const import (
    DOMAIN,
    QUEUE_STATE_IDLE,
    QUEUE_STATE_PAUSED,
    QUEUE_STATE_RUNNING,
    QUEUE_STATE_STOPPED,
    EXEC_MODE_SEQUENTIAL,
    EXEC_MODE_PARALLEL,
    EXEC_MODE_DISABLED,
    EXEC_MODE_MANUAL_ONLY,
    ITEM_STATUS_PENDING,
    ITEM_STATUS_APPROVED,
    ITEM_STATUS_INSTALLING,
    ITEM_STATUS_COMPLETED,
    ITEM_STATUS_FAILED,
    ITEM_STATUS_SKIPPED,
    ITEM_STATUS_WAITING_APPROVAL,
    INTEGRATION_GROUP_MAP,
    DEFAULT_GROUP_MODES,
    GROUP_DISPLAY_NAMES,
    GROUP_EXECUTION_ORDER,
    GROUP_ZWAVE,
    GROUP_HA_CORE,
    GROUP_HA_OS,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_AREAS,
    CONF_EXCLUDE_LABELS,
    CONF_GROUP_MODES,
    CONF_ZWAVE_MAINS_ONLY,
    CONF_INSTALL_DELAY,
    CONF_INSTALL_TIMEOUT,
    CONF_MAX_RETRIES,
    CONF_MAINTENANCE_WINDOW_ENABLED,
    CONF_MAINTENANCE_WINDOW_START,
    CONF_MAINTENANCE_WINDOW_END,
    CONF_STOP_ON_FAILURE,
    CONF_SKIP_UNAVAILABLE,
    DEFAULT_INSTALL_DELAY,
    DEFAULT_INSTALL_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class QueueItem:
    """Represents a single update in the queue."""

    def __init__(self, entity_id: str, group: str = "other") -> None:
        self.entity_id = entity_id
        self.group = group
        self.retries = 0
        self.status = ITEM_STATUS_PENDING
        self.error: str | None = None
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.friendly_name: str | None = None
        self.installed_version: str | None = None
        self.latest_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "entity_id": self.entity_id,
            "group": self.group,
            "retries": self.retries,
            "status": self.status,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "friendly_name": self.friendly_name,
            "installed_version": self.installed_version,
            "latest_version": self.latest_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueItem":
        """Deserialize from dict."""
        item = cls(data["entity_id"], data.get("group", "other"))
        item.retries = data.get("retries", 0)
        item.status = data.get("status", ITEM_STATUS_PENDING)
        item.error = data.get("error")
        item.friendly_name = data.get("friendly_name")
        item.installed_version = data.get("installed_version")
        item.latest_version = data.get("latest_version")
        if data.get("started_at"):
            item.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            item.completed_at = datetime.fromisoformat(data["completed_at"])
        return item


class UpdateQueueManager:
    """Manages the update queue with per-group execution modes.

    Key features:
    - Per-group execution modes: sequential, parallel, disabled, manual_only
    - Z-Wave is ALWAYS forced sequential (safety override, never parallel)
    - HA Core/OS is ALWAYS forced sequential (safety override)
    - Manual approval workflow for manual_only groups
    - Group-by-group processing in defined execution order
    - Battery device detection for Z-Wave mains-only filtering
    - Persistence via HA Store API
    """

    def __init__(self, hass: HomeAssistant, options: dict[str, Any]) -> None:
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

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

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
        """Return a copy of the current queue."""
        return list(self._queue)

    @property
    def pending_count(self) -> int:
        """Return the number of pending + approved updates."""
        return len(
            [i for i in self._queue if i.status in (ITEM_STATUS_PENDING, ITEM_STATUS_APPROVED)]
        )

    @property
    def waiting_approval_count(self) -> int:
        """Return the number of items waiting for manual approval."""
        return len([i for i in self._queue if i.status == ITEM_STATUS_WAITING_APPROVAL])

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

    @property
    def queue_summary(self) -> list[dict[str, Any]]:
        """Return a lightweight summary of every queue item for sensor attrs."""
        return [
            {
                "entity_id": i.entity_id,
                "group": i.group,
                "group_name": GROUP_DISPLAY_NAMES.get(i.group, i.group),
                "status": i.status,
                "friendly_name": i.friendly_name,
                "installed_version": i.installed_version,
                "latest_version": i.latest_version,
                "retries": i.retries,
                "error": i.error,
            }
            for i in self._queue
        ]

    # ------------------------------------------------------------------
    # Listener management
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_group_mode(self, group: str) -> str:
        """Return the execution mode for a group, respecting user overrides."""
        modes = self.options.get(CONF_GROUP_MODES, {})
        return modes.get(group, DEFAULT_GROUP_MODES.get(group, EXEC_MODE_MANUAL_ONLY))

    def _classify_entity(self, platform: str) -> str:
        """Map an HA integration platform string to our group name."""
        return INTEGRATION_GROUP_MAP.get(platform, "other")

    def _is_in_maintenance_window(self) -> bool:
        """Check if current time is within the maintenance window."""
        if not self.options.get(CONF_MAINTENANCE_WINDOW_ENABLED, False):
            return True  # No window restriction
        now = datetime.now().time()
        start = time.fromisoformat(
            self.options.get(CONF_MAINTENANCE_WINDOW_START, "02:00")
        )
        end = time.fromisoformat(
            self.options.get(CONF_MAINTENANCE_WINDOW_END, "05:00")
        )
        if start <= end:
            return start <= now <= end
        # Crosses midnight
        return now >= start or now <= end

    def _is_battery_device(self, entity_entry: er.RegistryEntry) -> bool:
        """Best-effort check if a device is battery-powered (Z-Wave)."""
        try:
            from homeassistant.helpers import device_registry as dr

            dev_reg = dr.async_get(self.hass)
            if entity_entry.device_id:
                device = dev_reg.async_get(entity_entry.device_id)
                if device:
                    ent_reg = er.async_get(self.hass)
                    for ent in er.async_entries_for_device(ent_reg, device.id):
                        if (
                            ent.entity_id.startswith("sensor.")
                            and "battery" in ent.entity_id
                        ):
                            return True
                        st = self.hass.states.get(ent.entity_id)
                        if st and st.attributes.get("device_class") == "battery":
                            return True
        except Exception:  # noqa: BLE001
            pass
        return False

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def async_discover_updates(self) -> list[QueueItem]:
        """Discover all update entities with available updates and classify."""
        ent_reg = er.async_get(self.hass)

        exclude_entities = set(self.options.get(CONF_EXCLUDE_ENTITIES, []))
        exclude_areas = set(self.options.get(CONF_EXCLUDE_AREAS, []))
        exclude_labels = set(self.options.get(CONF_EXCLUDE_LABELS, []))
        zwave_mains_only = self.options.get(CONF_ZWAVE_MAINS_ONLY, True)

        candidates: list[QueueItem] = []

        for entity_entry in ent_reg.entities.values():
            if not entity_entry.entity_id.startswith("update."):
                continue
            if entity_entry.disabled:
                continue
            if entity_entry.entity_id in exclude_entities:
                continue
            if exclude_areas and entity_entry.area_id in exclude_areas:
                continue
            if exclude_labels and hasattr(entity_entry, "labels"):
                if entity_entry.labels and entity_entry.labels.intersection(
                    exclude_labels
                ):
                    continue

            state = self.hass.states.get(entity_entry.entity_id)
            if state is None or state.state != STATE_ON:
                continue

            if self.options.get(CONF_SKIP_UNAVAILABLE, True):
                if state.state == "unavailable":
                    continue

            group = self._classify_entity(entity_entry.platform)
            mode = self._get_group_mode(group)

            # Disabled groups are completely skipped
            if mode == EXEC_MODE_DISABLED:
                continue

            # Z-Wave mains-only filter
            if group == GROUP_ZWAVE and zwave_mains_only:
                if self._is_battery_device(entity_entry):
                    _LOGGER.debug(
                        "Skipping battery Z-Wave device: %s",
                        entity_entry.entity_id,
                    )
                    continue

            item = QueueItem(entity_entry.entity_id, group)
            item.friendly_name = (
                state.attributes.get("friendly_name") or entity_entry.entity_id
            )
            item.installed_version = state.attributes.get("installed_version")
            item.latest_version = state.attributes.get("latest_version")

            if mode == EXEC_MODE_MANUAL_ONLY:
                item.status = ITEM_STATUS_WAITING_APPROVAL
            else:
                item.status = ITEM_STATUS_PENDING

            candidates.append(item)

        _LOGGER.info("Discovered %d eligible update entities", len(candidates))
        return candidates

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    async def async_refresh_candidates(self) -> int:
        """Refresh the queue: add new candidates, remove stale ones."""
        candidates = await self.async_discover_updates()
        candidate_ids = {c.entity_id for c in candidates}
        existing_ids = {item.entity_id for item in self._queue}

        new_count = 0
        for candidate in candidates:
            if candidate.entity_id not in existing_ids:
                self._queue.append(candidate)
                new_count += 1

        # Keep items that are still candidates OR are actively being processed
        self._queue = [
            item
            for item in self._queue
            if item.entity_id in candidate_ids
            or item.status
            in (ITEM_STATUS_INSTALLING, ITEM_STATUS_COMPLETED, ITEM_STATUS_FAILED)
        ]

        # Sort by group execution order
        group_order = {g: i for i, g in enumerate(GROUP_EXECUTION_ORDER)}
        self._queue.sort(key=lambda x: group_order.get(x.group, 99))

        await self.async_save()
        self._notify_listeners()
        _LOGGER.info(
            "Refreshed candidates: %d total, %d new", len(self._queue), new_count
        )
        return len(self._queue)

    async def async_approve_item(self, entity_id: str) -> None:
        """Approve a manual_only item so it will be installed."""
        for item in self._queue:
            if (
                item.entity_id == entity_id
                and item.status == ITEM_STATUS_WAITING_APPROVAL
            ):
                item.status = ITEM_STATUS_APPROVED
                _LOGGER.info("Approved for update: %s", entity_id)
                self._notify_listeners()
                await self.async_save()
                return
        _LOGGER.warning("No item waiting approval for: %s", entity_id)

    async def async_approve_all(self) -> int:
        """Approve all items currently waiting for approval."""
        count = 0
        for item in self._queue:
            if item.status == ITEM_STATUS_WAITING_APPROVAL:
                item.status = ITEM_STATUS_APPROVED
                count += 1
        if count:
            _LOGGER.info("Approved %d items for update", count)
            self._notify_listeners()
            await self.async_save()
        return count

    async def async_start_queue(self) -> None:
        """Start processing the update queue."""
        if self._state == QUEUE_STATE_RUNNING:
            _LOGGER.warning("Queue is already running")
            return

        await self.async_refresh_candidates()

        runnable = [
            i
            for i in self._queue
            if i.status in (ITEM_STATUS_PENDING, ITEM_STATUS_APPROVED)
        ]
        if not runnable:
            _LOGGER.info("No updates ready to install")
            self._notify_listeners()
            return

        self._state = QUEUE_STATE_RUNNING
        self._notify_listeners()
        await self.async_save()
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
            self._current_item.status = ITEM_STATUS_SKIPPED
            self._current_item.completed_at = datetime.now()
            _LOGGER.info(
                "Skipping current update: %s", self._current_item.entity_id
            )
            self._current_item = None
            self._notify_listeners()

    async def async_install_entity(self, entity_id: str) -> None:
        """Install a specific entity immediately (outside queue)."""
        _LOGGER.info("Manual install requested for: %s", entity_id)
        await self._async_install_single(entity_id)

    async def async_install_all_eligible(self) -> None:
        """Shortcut: start the queue (discovers + installs)."""
        await self.async_start_queue()

    async def async_clear_queue(self) -> None:
        """Clear all items from the queue and reset counters."""
        self._queue.clear()
        self._current_item = None
        self._completed_count = 0
        self._failed_count = 0
        self._state = QUEUE_STATE_IDLE
        self._notify_listeners()
        await self.async_save()
        _LOGGER.info("Queue cleared")

    # ------------------------------------------------------------------
    # Processing loop
    # ------------------------------------------------------------------

    async def _async_process_queue(self) -> None:
        """Process the queue group-by-group in execution-order."""
        _LOGGER.info("Starting queue processing with %d items", len(self._queue))

        for group in GROUP_EXECUTION_ORDER:
            if self._state == QUEUE_STATE_STOPPED:
                break

            mode = self._get_group_mode(group)
            if mode == EXEC_MODE_DISABLED:
                continue

            group_items = [
                i
                for i in self._queue
                if i.group == group
                and i.status in (ITEM_STATUS_PENDING, ITEM_STATUS_APPROVED)
            ]
            if not group_items:
                continue

            _LOGGER.info(
                "Processing group '%s' (%d items, mode=%s)",
                GROUP_DISPLAY_NAMES.get(group, group),
                len(group_items),
                mode,
            )

            if mode == EXEC_MODE_SEQUENTIAL:
                await self._process_group_sequential(group_items)
            elif mode == EXEC_MODE_PARALLEL:
                # Safety overrides: Z-Wave and HA Core/OS are NEVER parallel
                if group == GROUP_ZWAVE:
                    _LOGGER.warning("Z-Wave forced to sequential for safety")
                    await self._process_group_sequential(group_items)
                elif group in (GROUP_HA_CORE, GROUP_HA_OS):
                    _LOGGER.warning("HA Core/OS forced to sequential for safety")
                    await self._process_group_sequential(group_items)
                else:
                    await self._process_group_parallel(group_items)
            elif mode == EXEC_MODE_MANUAL_ONLY:
                approved = [
                    i for i in group_items if i.status == ITEM_STATUS_APPROVED
                ]
                if approved:
                    await self._process_group_sequential(approved)

        # Done
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

    async def _process_group_sequential(self, items: list[QueueItem]) -> None:
        """Install items one at a time, waiting for each to finish."""
        for item in items:
            if self._state == QUEUE_STATE_STOPPED:
                break

            # Wait while paused
            while self._state == QUEUE_STATE_PAUSED:
                await asyncio.sleep(5)
                if self._state == QUEUE_STATE_STOPPED:
                    return

            # Maintenance window check
            if not self._is_in_maintenance_window():
                _LOGGER.info("Outside maintenance window, waiting...")
                while not self._is_in_maintenance_window():
                    await asyncio.sleep(60)
                    if self._state == QUEUE_STATE_STOPPED:
                        return

            self._current_item = item
            item.status = ITEM_STATUS_INSTALLING
            item.started_at = datetime.now()
            self._notify_listeners()

            success = await self._async_install_single(item.entity_id)
            await self._handle_install_result(item, success)

            self._current_item = None
            self._notify_listeners()
            await self.async_save()

            delay = self.options.get(CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY)
            if delay > 0 and self._state == QUEUE_STATE_RUNNING:
                await asyncio.sleep(delay)

    async def _process_group_parallel(self, items: list[QueueItem]) -> None:
        """Install all items in parallel, wait for all to finish."""
        if not self._is_in_maintenance_window():
            _LOGGER.info("Outside maintenance window, waiting...")
            while not self._is_in_maintenance_window():
                await asyncio.sleep(60)
                if self._state == QUEUE_STATE_STOPPED:
                    return

        _LOGGER.info("Installing %d items in parallel", len(items))
        for item in items:
            item.status = ITEM_STATUS_INSTALLING
            item.started_at = datetime.now()
        self._notify_listeners()

        tasks = [self._async_install_single(item.entity_id) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item, result in zip(items, results):
            if isinstance(result, Exception):
                await self._handle_install_result(item, False, str(result))
            else:
                await self._handle_install_result(item, result)

        self._notify_listeners()
        await self.async_save()

    # ------------------------------------------------------------------
    # Install helpers
    # ------------------------------------------------------------------

    async def _handle_install_result(
        self, item: QueueItem, success: bool, error_msg: str | None = None
    ) -> None:
        """Record the result of an install attempt."""
        if success:
            item.status = ITEM_STATUS_COMPLETED
            item.completed_at = datetime.now()
            self._last_success = item.entity_id
            self._completed_count += 1
            _LOGGER.info("Successfully updated: %s", item.entity_id)
        else:
            max_retries = self.options.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES)
            item.retries += 1
            item.error = error_msg
            if item.retries >= max_retries:
                item.status = ITEM_STATUS_FAILED
                item.completed_at = datetime.now()
                self._last_failure = item.entity_id
                self._failed_count += 1
                _LOGGER.error(
                    "Update failed after %d retries: %s",
                    item.retries,
                    item.entity_id,
                )
                if self.options.get(CONF_STOP_ON_FAILURE, False):
                    _LOGGER.info(
                        "Stopping queue on failure (stop_on_failure=true)"
                    )
                    self._state = QUEUE_STATE_STOPPED
            else:
                item.status = ITEM_STATUS_PENDING
                _LOGGER.warning(
                    "Update failed, will retry (%d/%d): %s",
                    item.retries,
                    max_retries,
                    item.entity_id,
                )

    async def _async_install_single(self, entity_id: str) -> bool:
        """Install one update entity and poll for completion."""
        _LOGGER.info("Installing update: %s", entity_id)

        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning("Entity not found: %s", entity_id)
            return False
        if state.state != STATE_ON:
            _LOGGER.info(
                "No update available for %s (state=%s)", entity_id, state.state
            )
            return True  # Consider it done

        try:
            await self.hass.services.async_call(
                "update",
                "install",
                {"entity_id": entity_id},
                blocking=False,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "Failed to call update.install for %s: %s", entity_id, err
            )
            return False

        timeout = self.options.get(CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT)
        elapsed = 0
        poll_interval = 10

        while elapsed < timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            if self._state == QUEUE_STATE_STOPPED:
                return False

            state = self.hass.states.get(entity_id)
            if state is None:
                _LOGGER.warning(
                    "Entity disappeared during update: %s", entity_id
                )
                return False

            in_progress = state.attributes.get("in_progress")
            if in_progress is True or (
                isinstance(in_progress, (int, float)) and in_progress > 0
            ):
                continue

            if state.state != STATE_ON:
                _LOGGER.info("Update completed for %s", entity_id)
                return True

            if in_progress is False or in_progress is None:
                if elapsed > 60:
                    _LOGGER.warning("Update stalled for %s", entity_id)
                    return False

        _LOGGER.error(
            "Update timed out after %ds for %s", timeout, entity_id
        )
        return False

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def async_shutdown(self) -> None:
        """Shut down the queue manager."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.async_save()
