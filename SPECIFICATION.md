# SH Auto Update Manager — Specification

by **Smarter Homes LLC** — [smarter.homes](https://smarter.homes)

## Overview

A HACS custom integration for Home Assistant that manages and automates the installation of all available updates (firmware, software, add-ons) through a sequential queue with configurable rules, filtering, scheduling, and failure handling.

---

## Architecture

### Core Components

```
┌─────────────────────────────────────────────┐
│              Config Flow / Options           │
│  (config_flow.py)                            │
│  Setup wizard + advanced settings UI         │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│           Queue Manager                      │
│  (queue_manager.py)                          │
│  - Discovery: scans entity registry          │
│  - Filtering: integration/area/label/entity  │
│  - Queue: ordered list of QueueItems         │
│  - Executor: sequential install loop         │
│  - Persistence: Store API for restart safety │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│           Entity Platforms                   │
│  sensor.py  │  button.py  │  switch.py       │
│  7 sensors  │  4 buttons  │  2 switches      │
│  Status, counts, targets  │  Controls        │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│           Services                           │
│  (services.yaml + __init__.py)               │
│  8 service actions for automation/scripting  │
└─────────────────────────────────────────────┘
```

### Data Flow

1. **Discovery** — Entity registry is scanned for `update.*` entities
2. **Filtering** — Entities are filtered by options (integration, area, labels, state, category)
3. **Queueing** — Eligible entities are added as `QueueItem` objects (pending)
4. **Execution** — Items are processed sequentially:
   - Call `update.install` on the entity
   - Poll `in_progress` attribute until complete or timeout
   - Mark as completed/failed
   - Apply delay, then next item
5. **Persistence** — Queue state saved to `Store` after each change

---

## Configuration Schema

### Initial Setup (Config Flow)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `auto_update` | bool | `false` | Automatically install updates when discovered |
| `mains_powered_only` | bool | `false` | Skip battery-powered devices |
| `category_filter` | select | `all` | `all` or `firmware` only |

### Options Flow (Advanced Settings)

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `auto_update` | bool | `false` | — | Auto-install mode |
| `mains_powered_only` | bool | `false` | — | Skip battery devices |
| `one_at_a_time` | bool | `true` | — | Sequential install |
| `category_filter` | select | `all` | `all`, `firmware` | Update category |
| `install_delay` | int | `15` | 0–300 | Seconds between installs |
| `install_timeout` | int | `7200` | 60–14400 | Seconds per update timeout |
| `max_retries` | int | `2` | 0–10 | Retries per failed update |
| `stop_on_failure` | bool | `false` | — | Stop queue on first failure |
| `skip_unavailable` | bool | `true` | — | Skip unavailable entities |
| `maintenance_window_enabled` | bool | `false` | — | Enable time window |
| `maintenance_window_start` | string | `02:00` | HH:MM | Window start time |
| `maintenance_window_end` | string | `05:00` | HH:MM | Window end time |
| `include_integrations` | string | `""` | CSV | Only include these integrations |
| `exclude_entities` | string | `""` | CSV | Skip these entity IDs |
| `exclude_areas` | string | `""` | CSV | Skip entities in these areas |
| `exclude_labels` | string | `""` | CSV | Skip entities with these labels |

---

## Queue Manager

### QueueItem States

```
pending → installing → completed
                    → failed (retries exhausted)
                    → skipped (user skip or unavailable)
```

### Queue States

| State | Description |
|-------|-------------|
| `idle` | No queue running, waiting for user action or auto-trigger |
| `running` | Queue is actively processing updates |
| `paused` | Queue is paused, will resume on user action |
| `stopped` | Queue was stopped, requires manual restart |

### Discovery Logic

```python
# Pseudocode for entity discovery
for entity in entity_registry:
    if not entity.startswith("update."):  skip
    if entity.disabled:                   skip
    if entity in exclude_entities:        skip
    if entity.area in exclude_areas:      skip
    if entity.labels & exclude_labels:    skip
    if include_integrations and entity.platform not in include_integrations:  skip
    if state != "on":                     skip  # no update available
    if category_filter == "firmware" and device_class != "firmware":  skip
    if skip_unavailable and state == "unavailable":  skip
    → add to queue
```

### Install Logic

```python
# Pseudocode for single entity install
1. Verify entity state == "on" (update available)
2. Call update.install(entity_id=...)
3. Poll every 10 seconds:
   - If in_progress: continue waiting
   - If state != "on": update complete → success
   - If in_progress is False and state is "on" and elapsed > 60s: stalled → failure
   - If elapsed > timeout: timeout → failure
4. On success: mark completed, record last_success
5. On failure: increment retries
   - If retries >= max_retries: mark failed, record last_failure
   - Else: reset to pending for retry
   - If stop_on_failure: stop queue
```

---

## Services API

### sh_update_manager.start_queue
- **Parameters:** none
- **Effect:** Discovers updates, builds queue, starts sequential processing

### sh_update_manager.pause_queue
- **Parameters:** none
- **Effect:** Pauses after current update finishes

### sh_update_manager.resume_queue
- **Parameters:** none
- **Effect:** Resumes a paused queue

### sh_update_manager.stop_queue
- **Parameters:** none
- **Effect:** Immediately stops queue processing

### sh_update_manager.skip_current
- **Parameters:** none
- **Effect:** Marks current update as skipped, moves to next

### sh_update_manager.refresh_candidates
- **Parameters:** none
- **Effect:** Rescans entity registry, adds new candidates, removes stale ones

### sh_update_manager.install_all_eligible
- **Parameters:** none
- **Effect:** Same as start_queue (discover + install all)

### sh_update_manager.install_entity
- **Parameters:**
  - `entity_id` (required): Target update entity (e.g., `update.kitchen_light_firmware`)
- **Effect:** Immediately installs the specified update

---

## Entity Specifications

### Sensors

| Entity ID | Name | Unit | Value |
|-----------|------|------|-------|
| `sensor.sh_auto_update_manager_queue_status` | Queue Status | — | idle/running/paused/stopped |
| `sensor.sh_auto_update_manager_pending_updates` | Pending Updates | updates | int |
| `sensor.sh_auto_update_manager_current_update` | Current Update Target | — | entity_id or None |
| `sensor.sh_auto_update_manager_last_success` | Last Success | — | entity_id or None |
| `sensor.sh_auto_update_manager_last_failure` | Last Failure | — | entity_id or None |
| `sensor.sh_auto_update_manager_completed_count` | Completed Updates | updates | int |
| `sensor.sh_auto_update_manager_failed_count` | Failed Updates | updates | int |

### Buttons

| Entity ID | Name | Effect |
|-----------|------|--------|
| `button.sh_auto_update_manager_update_all_eligible` | Update All Eligible | Starts the queue |
| `button.sh_auto_update_manager_refresh_candidates` | Refresh Update Scan | Rescans updates |
| `button.sh_auto_update_manager_stop_queue` | Stop Queue | Stops queue |
| `button.sh_auto_update_manager_skip_current` | Skip Current Update | Skips current |

### Switches

| Entity ID | Name | Effect |
|-----------|------|--------|
| `switch.sh_auto_update_manager_auto_update` | Auto Update Enabled | Toggles auto mode |
| `switch.sh_auto_update_manager_pause_queue` | Pause Queue | Toggles pause |

---

## Persistence

Queue state is persisted using Home Assistant's `Store` API:

- **Storage key:** `sh_update_manager.queue`
- **Storage version:** 1
- **Persisted data:**
  - Queue items (entity_id, status, retries, timestamps)
  - Queue state (idle/running/paused/stopped)
  - Counters (completed, failed)
  - Last success/failure entity IDs

This ensures the queue survives Home Assistant restarts.

---

## Future Enhancements

### v1.1 (Planned)
- [ ] Notification service calls (before/after updates, on failure)
- [ ] Per-entity update policies (always, never, manual-approval)
- [ ] Detailed update history log entity

### v1.2 (Planned)
- [ ] Custom Lovelace card for queue visualization
- [ ] Protocol-specific adapters (Z-Wave wake-up handling)
- [ ] Update grouping by device type

### v2.0 (Future)
- [ ] Dashboard panel with drag-and-drop queue ordering
- [ ] Backup-before-update integration
- [ ] Rollback support (where the update platform supports it)
- [ ] Multi-instance support for different rule sets

---

## Version History

### v1.0.0 — 2026-04-08
- Initial release
- Queue manager with sequential installation
- Config flow + Options flow
- 7 sensors, 4 buttons, 2 switches
- 8 service actions
- Persistent queue state
- Maintenance window
- Integration/area/label/entity filtering
- Mains-powered-only Z-Wave safety mode
