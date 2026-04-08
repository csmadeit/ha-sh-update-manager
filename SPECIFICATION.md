# SH Auto Update Manager — Specification

by **Smarter Homes LLC** — [smarter.homes](https://smarter.homes)

## Overview

A HACS custom integration for Home Assistant that manages updates through **named queues**. Each queue independently discovers, filters, and installs updates matching its rules — replacing the v1.1 single-global-queue architecture.

---

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────┐
│           Config Flow / Options                  │
│  (config_flow.py)                                │
│  Setup: ask auto-create → select queues           │
│  Options: list → add/edit/remove queues          │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│           Queue Coordinator                      │
│  (queue_manager.py — QueueCoordinator)           │
│  - Manages all NamedQueue instances              │
│  - Global operations: scan_all, start_all, stop  │
│  - Persistence via Store API                     │
│  - Listener management for global sensors        │
└──────────────┬──────────────────────────────────┘
               │ owns N queues
┌──────────────▼──────────────────────────────────┐
│           Named Queue                            │
│  (queue_manager.py — NamedQueue)                 │
│  - Config: match rule, exec mode, trigger mode   │
│  - Discovery: matches entities by rule           │
│  - Processing: sequential or parallel            │
│  - State machine: idle → running → idle/stopped  │
│  - Z-Wave battery detection                      │
│  - Per-queue listeners for sensors               │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│           Entity Platforms                        │
│  sensor.py  │  button.py  │  switch.py           │
│  Global overview + per-queue sensors             │
│  Global + per-queue buttons and switches         │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│           Services                               │
│  (services.yaml + __init__.py)                   │
│  3 global + 6 per-queue service actions          │
└─────────────────────────────────────────────────┘
```

### Data Flow

1. **Configuration** — User creates/edits queues via options flow, stored in `config_entry.options["queues"]`
2. **Initialization** — `QueueCoordinator` creates `NamedQueue` instances from config
3. **Discovery** — Each queue scans entity registry for `update.*` entities matching its rule
4. **Matching** — Entities matched by integration platform, area, label, or entity ID
5. **Filtering** — Skip disabled, unavailable, battery (if mains-only), no-update-available
6. **Queueing** — Matched entities added as `QueueItem` objects with pending status
7. **Execution** — Sequential (one at a time) or parallel (all at once)
8. **Persistence** — State saved to Store after each change

---

## Queue Configuration

### Per-Queue Config Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | — | Queue display name (e.g., "Z-Wave Firmware") |
| `match_type` | enum | `integration` | How to select entities: integration, area, label, entity |
| `match_value` | string | `""` | Comma-separated values for the match rule |
| `exec_mode` | enum | `sequential` | How to process: sequential or parallel |
| `trigger_mode` | enum | `manual` | When to run: manual or auto_on_scan |
| `zwave_mains_only` | bool | `false` | Skip battery Z-Wave devices |
| `stop_on_failure` | bool | `false` | Stop queue on first failure |
| `skip_unavailable` | bool | `true` | Skip unavailable entities |
| `install_delay` | int | `15` | Seconds between sequential installs (0–300) |
| `install_timeout` | int | `7200` | Seconds per update timeout (60–14400) |
| `max_retries` | int | `2` | Retries per failed update (0–10) |
| `enabled` | bool | `true` | Whether the queue is active |

### Default Queues

| Name | Match Type | Match Value | Exec Mode | Z-Wave Mains Only |
|------|-----------|-------------|-----------|-------------------|
| Z-Wave Firmware | integration | zwave_js,zwave | sequential | true |
| ESPHome Devices | integration | esphome | sequential | false |
| HACS Updates | integration | hacs | sequential | false |
| Add-ons | integration | hassio_addons,hassio | sequential | false |
| Other Updates | integration | matter,mqtt | sequential | false |

HA Core and HA OS are **not** included in any default queue.

### Integration-to-Group Mapping

| HA Platform | Group Key |
|------------|-----------|
| `zwave_js`, `zwave` | zwave |
| `esphome` | esphome |
| `hacs` | hacs |
| `homeassistant`, `update` | ha_core |
| `hassio` | ha_os |
| `hassio_addons` | addons |
| `matter` | matter |
| `mqtt` | mqtt |
| *(anything else)* | other |

### Safety Overrides

These apply regardless of queue configuration:

1. **Z-Wave** — Always forced to sequential. Z-Wave firmware updates must complete one at a time.
2. **HA Core** — Always forced to sequential if a queue is created for it.
3. **HA OS** — Always forced to sequential if a queue is created for it.

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
| `idle` | Not running, waiting for user action or auto-trigger |
| `running` | Actively processing updates |
| `paused` | Paused, will resume on user action |
| `stopped` | Stopped by user or failure, requires manual restart |

### Discovery Logic (per queue)

```python
for entity in entity_registry:
    if not entity.startswith("update."):     skip
    if entity.disabled:                      skip
    if state != "on":                        skip  # no update available
    if skip_unavailable and unavailable:     skip

    if match_type == "integration":
        if entity.platform not in match_values:  skip
    elif match_type == "area":
        if entity.area_id not in match_values:   skip
    elif match_type == "label":
        if not entity.labels & match_values:     skip
    elif match_type == "entity":
        if entity.entity_id not in match_values: skip

    if zwave_mains_only and is_battery(entity):  skip

    add to queue as pending
```

### Install Logic

```python
1. Set item status to "installing"
2. Call update.install(entity_id=...)
3. Poll every 5 seconds:
   - If in_progress is False and state != "on": success
   - If elapsed > timeout: failure
4. On success: mark completed, increment completed_count
5. On failure: increment retries
   - If retries >= max_retries: mark failed
   - Else: retry
   - If stop_on_failure: stop queue
6. Sequential: wait install_delay before next item
```

---

## Services API

### Global Services

#### sh_update_manager.scan_all
- **Parameters:** none
- **Effect:** Scans all enabled queues for new update entities

#### sh_update_manager.start_all
- **Parameters:** none
- **Effect:** Starts all enabled queues that have pending updates

#### sh_update_manager.stop_all
- **Parameters:** none
- **Effect:** Stops all currently running queues

### Per-Queue Services

All per-queue services require a `queue_name` parameter (string, the queue's display name).

#### sh_update_manager.start_queue
- **Parameters:** `queue_name` (required)
- **Effect:** Scans and starts processing the named queue

#### sh_update_manager.stop_queue
- **Parameters:** `queue_name` (required)
- **Effect:** Stops the named queue

#### sh_update_manager.pause_queue
- **Parameters:** `queue_name` (required)
- **Effect:** Pauses the named queue (current update finishes)

#### sh_update_manager.resume_queue
- **Parameters:** `queue_name` (required)
- **Effect:** Resumes a paused queue

#### sh_update_manager.skip_current
- **Parameters:** `queue_name` (required)
- **Effect:** Skips the currently installing update in the named queue

#### sh_update_manager.clear_queue
- **Parameters:** `queue_name` (required)
- **Effect:** Clears all items and resets counters for the named queue

---

## Entity Specifications

### Global Sensors (1)

| Entity ID | Name | Value | Extra Attributes |
|-----------|------|-------|-----------------|
| `sensor.*_global_overview` | Update Manager Overview | idle/running/paused | total_queues, total_pending, total_completed, total_failed, queues (summary list) |

### Per-Queue Sensors (3 per queue)

| Entity ID | Name | Value | Extra Attributes |
|-----------|------|-------|-----------------|
| `sensor.*_{slug}_status` | {Queue} Status | idle/running/paused/stopped | enabled, exec_mode, trigger_mode, pending, completed, failed, last_success, last_failure, current_item |
| `sensor.*_{slug}_pending` | {Queue} Pending | int (count) | — |
| `sensor.*_{slug}_items` | {Queue} Items | int (total count) | items (full list with entity_id, friendly_name, status, versions, retries, error) |

### Global Buttons (3)

| Entity ID | Name | Effect |
|-----------|------|--------|
| `button.*_scan_all` | Scan All Queues | Scan all enabled queues |
| `button.*_start_all` | Start All Queues | Start all enabled queues |
| `button.*_stop_all` | Stop All Queues | Stop all running queues |

### Per-Queue Buttons (3 per queue)

| Entity ID | Name | Effect |
|-----------|------|--------|
| `button.*_{slug}_start` | Start {Queue} | Start this queue |
| `button.*_{slug}_stop` | Stop {Queue} | Stop this queue |
| `button.*_{slug}_skip` | Skip Current in {Queue} | Skip current update |

### Global Switches (1)

| Entity ID | Name | Effect |
|-----------|------|--------|
| `switch.*_pause_all` | Pause All Queues | Pause/resume all running queues |

### Per-Queue Switches (2 per queue)

| Entity ID | Name | Effect |
|-----------|------|--------|
| `switch.*_{slug}_pause` | Pause {Queue} | Pause/resume this queue |
| `switch.*_{slug}_enabled` | Enable {Queue} | Enable/disable this queue |

---

## Persistence

Queue state is persisted using Home Assistant's `Store` API:

- **Storage key:** `sh_update_manager.queues`
- **Storage version:** 3
- **Persisted data per queue:**
  - Queue items (entity_id, group, status, retries, timestamps, friendly_name, versions, error)
  - Queue state (idle/running/paused/stopped)
  - Counters (completed, failed)
  - Last success/failure entity IDs
  - Queue config

This ensures all queues survive Home Assistant restarts.

---

## Future Enhancements

### v1.3 (Planned)
- [ ] Scheduled triggers (run queue at specific times, cron-like)
- [ ] Notification service calls (before/after updates, on failure)
- [ ] Detailed update history log entity per queue
- [ ] Custom Lovelace card for queue visualization

### v2.0 (Future)
- [ ] Dashboard sidebar panel with full queue management UI
- [ ] Drag-and-drop queue ordering
- [ ] Protocol-specific adapters (Z-Wave wake-up handling)
- [ ] Backup-before-update integration
- [ ] Rollback support (where the update platform supports it)

---

## Version History

### v1.2.1 — 2026-04-08
- Interactive setup flow — asks whether to auto-create default queues
- Queue selection step with checkboxes for each default queue template
- Option to start with zero queues and build from scratch

### v1.2.0 — 2026-04-08
- Queue-based architecture — multiple named queues replace single global queue
- Per-queue configuration: match rules, execution modes, trigger modes
- Auto-created default queues (Z-Wave, ESPHome, HACS, Add-ons, Other)
- Per-queue entities (sensors, buttons, switches)
- Global controls (overview sensor, scan/start/stop buttons, pause-all switch)
- Queue management UI in options flow
- HA Core/OS excluded from all default queues
- 9 services (3 global + 6 per-queue)

### v1.1.0 — 2026-04-08
- Per-group execution modes (sequential, parallel, disabled, manual_only)
- 9 update groups with integration-to-group mapping
- Z-Wave always-sequential safety override
- Manual approval workflow
- Multi-step options flow
- 8 sensors, 6 buttons, 2 switches, 10 services

### v1.0.0 — 2026-04-08
- Initial release
- Queue manager with sequential installation
- Config flow + Options flow
- 7 sensors, 4 buttons, 2 switches, 8 services
- Persistent queue state, maintenance window, filtering
