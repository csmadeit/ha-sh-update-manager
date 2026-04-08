"""Queue manager for SH Auto Update Manager v1.2.0.

Each named queue independently discovers, filters, and installs updates
matching its rules. Queues run independently of each other.

by Smarter Homes LLC — smarter.homes
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
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
    ITEM_STATUS_PENDING,
    ITEM_STATUS_INSTALLING,
    ITEM_STATUS_COMPLETED,
    ITEM_STATUS_FAILED,
    ITEM_STATUS_SKIPPED,
    MATCH_INTEGRATION,
    MATCH_AREA,
    MATCH_LABEL,
    MATCH_ENTITY,
    INTEGRATION_GROUP_MAP,
    FORCE_SEQUENTIAL_GROUPS,
    GROUP_ZWAVE,
    CONF_MATCH_TYPE,
    CONF_MATCH_VALUE,
    CONF_EXEC_MODE,
    CONF_TRIGGER_MODE,
    CONF_ZWAVE_MAINS_ONLY,
    CONF_STOP_ON_FAILURE,
    CONF_SKIP_UNAVAILABLE,
    CONF_INSTALL_DELAY,
    CONF_INSTALL_TIMEOUT,
    CONF_MAX_RETRIES,
    CONF_QUEUE_ENABLED,
    DEFAULT_INSTALL_DELAY,
    DEFAULT_INSTALL_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class QueueItem:
    """Represents a single update in a queue."""

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


def _slugify(name: str) -> str:
    """Convert a queue name to a slug for entity IDs."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "queue"


class NamedQueue:
    """A single named update queue with independent config and state."""

    def __init__(self, hass: HomeAssistant, queue_config: dict[str, Any]) -> None:
        self.hass = hass
        self.config = dict(queue_config)
        self.name: str = queue_config.get("name", "Unnamed Queue")
        self.slug = _slugify(self.name)
        self._items: list[QueueItem] = []
        self._state = QUEUE_STATE_IDLE
        self._current_item: QueueItem | None = None
        self._task: asyncio.Task | None = None
        self._last_success: str | None = None
        self._last_failure: str | None = None
        self._completed_count = 0
        self._failed_count = 0
        self._listeners: list[Any] = []

    @property
    def enabled(self) -> bool:
        return self.config.get(CONF_QUEUE_ENABLED, True)

    @property
    def match_type(self) -> str:
        return self.config.get(CONF_MATCH_TYPE, MATCH_INTEGRATION)

    @property
    def match_value(self) -> str:
        return self.config.get(CONF_MATCH_VALUE, "")

    @property
    def exec_mode(self) -> str:
        mode = self.config.get(CONF_EXEC_MODE, EXEC_MODE_SEQUENTIAL)
        match_vals = {v.strip() for v in self.match_value.split(",")}
        for val in match_vals:
            group = INTEGRATION_GROUP_MAP.get(val, val)
            if group in FORCE_SEQUENTIAL_GROUPS:
                return EXEC_MODE_SEQUENTIAL
        return mode

    @property
    def trigger_mode(self) -> str:
        return self.config.get(CONF_TRIGGER_MODE, "manual")

    @property
    def zwave_mains_only(self) -> bool:
        return self.config.get(CONF_ZWAVE_MAINS_ONLY, False)

    @property
    def stop_on_failure(self) -> bool:
        return self.config.get(CONF_STOP_ON_FAILURE, False)

    @property
    def skip_unavailable(self) -> bool:
        return self.config.get(CONF_SKIP_UNAVAILABLE, True)

    @property
    def install_delay(self) -> int:
        return self.config.get(CONF_INSTALL_DELAY, DEFAULT_INSTALL_DELAY)

    @property
    def install_timeout(self) -> int:
        return self.config.get(CONF_INSTALL_TIMEOUT, DEFAULT_INSTALL_TIMEOUT)

    @property
    def max_retries(self) -> int:
        return self.config.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES)

    @property
    def state(self) -> str:
        return self._state

    @property
    def current_item(self) -> QueueItem | None:
        return self._current_item

    @property
    def items(self) -> list[QueueItem]:
        return list(self._items)

    @property
    def pending_count(self) -> int:
        return len([i for i in self._items if i.status == ITEM_STATUS_PENDING])

    @property
    def completed_count(self) -> int:
        return self._completed_count

    @property
    def failed_count(self) -> int:
        return self._failed_count

    @property
    def last_success(self) -> str | None:
        return self._last_success

    @property
    def last_failure(self) -> str | None:
        return self._last_failure

    @property
    def items_summary(self) -> list[dict[str, Any]]:
        return [
            {
                "entity_id": i.entity_id,
                "friendly_name": i.friendly_name,
                "status": i.status,
                "installed_version": i.installed_version,
                "latest_version": i.latest_version,
                "retries": i.retries,
                "error": i.error,
            }
            for i in self._items
        ]

    def register_listener(self, listener: Any) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: Any) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    @callback
    def _notify(self) -> None:
        for ln in self._listeners:
            ln()

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "items": [i.to_dict() for i in self._items],
            "state": self._state,
            "last_success": self._last_success,
            "last_failure": self._last_failure,
            "completed_count": self._completed_count,
            "failed_count": self._failed_count,
        }

    def load_state(self, data: dict[str, Any]) -> None:
        self._items = [QueueItem.from_dict(d) for d in data.get("items", [])]
        self._state = data.get("state", QUEUE_STATE_IDLE)
        self._last_success = data.get("last_success")
        self._last_failure = data.get("last_failure")
        self._completed_count = data.get("completed_count", 0)
        self._failed_count = data.get("failed_count", 0)

    def _entity_matches(self, entity_entry: er.RegistryEntry) -> bool:
        if self.match_type == MATCH_INTEGRATION:
            targets = {v.strip() for v in self.match_value.split(",") if v.strip()}
            return entity_entry.platform in targets
        if self.match_type == MATCH_AREA:
            targets = {v.strip() for v in self.match_value.split(",") if v.strip()}
            return entity_entry.area_id in targets if entity_entry.area_id else False
        if self.match_type == MATCH_LABEL:
            targets = {v.strip() for v in self.match_value.split(",") if v.strip()}
            if hasattr(entity_entry, "labels") and entity_entry.labels:
                return bool(entity_entry.labels.intersection(targets))
            return False
        if self.match_type == MATCH_ENTITY:
            targets = {v.strip() for v in self.match_value.split(",") if v.strip()}
            return entity_entry.entity_id in targets
        return False

    def _is_battery_device(self, entity_entry: er.RegistryEntry) -> bool:
        try:
            from homeassistant.helpers import device_registry as dr
            dev_reg = dr.async_get(self.hass)
            if entity_entry.device_id:
                device = dev_reg.async_get(entity_entry.device_id)
                if device:
                    ent_reg = er.async_get(self.hass)
                    for ent in er.async_entries_for_device(ent_reg, device.id):
                        if ent.entity_id.startswith("sensor.") and "battery" in ent.entity_id:
                            return True
                        st = self.hass.states.get(ent.entity_id)
                        if st and st.attributes.get("device_class") == "battery":
                            return True
        except Exception:
            pass
        return False

    async def async_scan(self) -> int:
        if not self.enabled:
            return 0
        ent_reg = er.async_get(self.hass)
        candidates: list[QueueItem] = []
        for entity_entry in ent_reg.entities.values():
            if not entity_entry.entity_id.startswith("update."):
                continue
            if entity_entry.disabled:
                continue
            if not self._entity_matches(entity_entry):
                continue
            state = self.hass.states.get(entity_entry.entity_id)
            if state is None or state.state != STATE_ON:
                continue
            if self.skip_unavailable and state.state == "unavailable":
                continue
            group = INTEGRATION_GROUP_MAP.get(entity_entry.platform, "other")
            if group == GROUP_ZWAVE and self.zwave_mains_only:
                if self._is_battery_device(entity_entry):
                    continue
            item = QueueItem(entity_entry.entity_id, group)
            item.friendly_name = (
                state.attributes.get("friendly_name") or entity_entry.entity_id
            )
            item.installed_version = state.attributes.get("installed_version")
            item.latest_version = state.attributes.get("latest_version")
            candidates.append(item)

        existing_ids = {i.entity_id for i in self._items}
        candidate_ids = {c.entity_id for c in candidates}
        new_count = 0
        for c in candidates:
            if c.entity_id not in existing_ids:
                self._items.append(c)
                new_count += 1
        self._items = [
            i for i in self._items
            if i.entity_id in candidate_ids
            or i.status in (ITEM_STATUS_INSTALLING, ITEM_STATUS_COMPLETED, ITEM_STATUS_FAILED)
        ]
        self._notify()
        _LOGGER.info(
            "Queue '%s': %d candidates, %d new, %d total",
            self.name, len(candidates), new_count, len(self._items),
        )
        return len(self._items)

    async def async_start(self) -> None:
        if self._state == QUEUE_STATE_RUNNING:
            return
        await self.async_scan()
        runnable = [i for i in self._items if i.status == ITEM_STATUS_PENDING]
        if not runnable:
            return
        self._state = QUEUE_STATE_RUNNING
        self._notify()
        self._task = self.hass.async_create_task(self._async_process())

    async def async_stop(self) -> None:
        self._state = QUEUE_STATE_STOPPED
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._current_item = None
        self._notify()

    async def async_pause(self) -> None:
        if self._state == QUEUE_STATE_RUNNING:
            self._state = QUEUE_STATE_PAUSED
            self._notify()

    async def async_resume(self) -> None:
        if self._state == QUEUE_STATE_PAUSED:
            self._state = QUEUE_STATE_RUNNING
            self._notify()

    async def async_skip_current(self) -> None:
        if self._current_item:
            self._current_item.status = ITEM_STATUS_SKIPPED
            self._current_item.completed_at = datetime.now()
            self._current_item = None
            self._notify()

    async def async_clear(self) -> None:
        self._items.clear()
        self._current_item = None
        self._completed_count = 0
        self._failed_count = 0
        self._state = QUEUE_STATE_IDLE
        self._notify()

    async def _async_process(self) -> None:
        try:
            if self.exec_mode == EXEC_MODE_PARALLEL:
                await self._process_parallel()
            else:
                await self._process_sequential()
        except asyncio.CancelledError:
            pass
        except Exception:
            _LOGGER.exception("Queue '%s': error", self.name)
        finally:
            if self._state == QUEUE_STATE_RUNNING:
                self._state = QUEUE_STATE_IDLE
            self._current_item = None
            self._notify()

    async def _process_sequential(self) -> None:
        for item in self._items:
            if self._state != QUEUE_STATE_RUNNING:
                break
            if item.status != ITEM_STATUS_PENDING:
                continue
            while self._state == QUEUE_STATE_PAUSED:
                await asyncio.sleep(1)
            if self._state != QUEUE_STATE_RUNNING:
                break
            self._current_item = item
            success = await self._install_item(item)
            self._current_item = None
            if not success and self.stop_on_failure:
                self._state = QUEUE_STATE_STOPPED
                break
            if self.install_delay > 0:
                await asyncio.sleep(self.install_delay)

    async def _process_parallel(self) -> None:
        pending = [i for i in self._items if i.status == ITEM_STATUS_PENDING]
        await asyncio.gather(
            *[self._install_item(i) for i in pending], return_exceptions=True
        )

    async def _install_item(self, item: QueueItem) -> bool:
        item.status = ITEM_STATUS_INSTALLING
        item.started_at = datetime.now()
        self._notify()
        for attempt in range(self.max_retries + 1):
            item.retries = attempt
            try:
                await self.hass.services.async_call(
                    "update", "install",
                    {"entity_id": item.entity_id},
                    blocking=True,
                )
                if await self._wait_for_completion(item):
                    item.status = ITEM_STATUS_COMPLETED
                    item.completed_at = datetime.now()
                    self._completed_count += 1
                    self._last_success = item.entity_id
                    self._notify()
                    return True
            except Exception as exc:
                item.error = str(exc)
            if attempt < self.max_retries:
                await asyncio.sleep(5)
        item.status = ITEM_STATUS_FAILED
        item.completed_at = datetime.now()
        self._failed_count += 1
        self._last_failure = item.entity_id
        self._notify()
        return False

    async def _wait_for_completion(self, item: QueueItem) -> bool:
        elapsed = 0
        while elapsed < self.install_timeout:
            state = self.hass.states.get(item.entity_id)
            if state is None:
                return True
            in_progress = state.attributes.get("in_progress")
            if in_progress is False or in_progress is None:
                if state.state != STATE_ON:
                    return True
            await asyncio.sleep(5)
            elapsed += 5
        item.error = f"Timed out after {self.install_timeout}s"
        return False

    async def async_shutdown(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


class QueueCoordinator:
    """Manages all named queues for a config entry."""

    def __init__(
        self, hass: HomeAssistant, queues_config: list[dict[str, Any]]
    ) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._queues: list[NamedQueue] = []
        self._listeners: list[Any] = []
        for qc in queues_config:
            self._queues.append(NamedQueue(hass, qc))

    @property
    def queues(self) -> list[NamedQueue]:
        return list(self._queues)

    def get_queue(self, name: str) -> NamedQueue | None:
        name_lower = name.lower()
        for q in self._queues:
            if q.name.lower() == name_lower:
                return q
        return None

    def get_queue_by_slug(self, slug: str) -> NamedQueue | None:
        for q in self._queues:
            if q.slug == slug:
                return q
        return None

    def add_queue(self, config: dict[str, Any]) -> NamedQueue:
        q = NamedQueue(self.hass, config)
        self._queues.append(q)
        self._notify_global()
        return q

    def remove_queue(self, name: str) -> bool:
        q = self.get_queue(name)
        if q:
            self._queues.remove(q)
            self._notify_global()
            return True
        return False

    def update_queue_config(
        self, name: str, new_config: dict[str, Any]
    ) -> bool:
        q = self.get_queue(name)
        if q:
            q.config.update(new_config)
            q.name = q.config.get("name", q.name)
            q.slug = _slugify(q.name)
            return True
        return False

    async def async_scan_all(self) -> dict[str, int]:
        results = {}
        for q in self._queues:
            if q.enabled:
                count = await q.async_scan()
                results[q.name] = count
        await self.async_save()
        self._notify_global()
        return results

    async def async_start_all(self) -> None:
        for q in self._queues:
            if q.enabled and q.pending_count > 0:
                await q.async_start()
        await self.async_save()

    async def async_stop_all(self) -> None:
        for q in self._queues:
            if q.state == QUEUE_STATE_RUNNING:
                await q.async_stop()
        await self.async_save()

    def register_global_listener(self, listener: Any) -> None:
        self._listeners.append(listener)

    def remove_global_listener(self, listener: Any) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    @callback
    def _notify_global(self) -> None:
        for ln in self._listeners:
            ln()

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not data or "queues" not in data:
            return
        saved = data["queues"]
        for q in self._queues:
            if q.name in saved:
                q.load_state(saved[q.name])

    async def async_save(self) -> None:
        data = {"queues": {q.name: q.to_dict() for q in self._queues}}
        await self._store.async_save(data)

    async def async_shutdown(self) -> None:
        for q in self._queues:
            await q.async_shutdown()
        await self.async_save()

    def get_all_queues_config(self) -> list[dict[str, Any]]:
        return [dict(q.config) for q in self._queues]
