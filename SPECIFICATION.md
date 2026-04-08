# SH Auto Update Manager — Specification

by **Smarter Homes LLC** — [smarter.homes](https://smarter.homes)

## Overview

A HACS custom integration for Home Assistant that manages and automates the installation of all available updates (firmware, software, add-ons) through a grouped queue with per-group execution modes, manual approval workflows, safety overrides, and configurable rules.

---

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────┐
│           Config Flow / Options                  │
│  (config_flow.py)                                │
│  Step 1: Global settings                         │
│  Step 2: Per-group execution modes               │
│  Step 3: Exclusion filters                       │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│           Queue Manager                          │
│  (queue_manager.py)                              │
│  - Discovery: scans entity registry              │
│  - Classification: maps entities → groups        │
│  - Filtering: area/label/entity exclusions       │
│  - Queue: ordered list of QueueItems by group    │
│  - Executor: per-group sequential/parallel       │
│  - Safety: Z-Wave + HA Core/OS forced sequential │
│  - Approval: manual_only workflow                │
│  - Persistence: Store API for restart safety     │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│           Entity Platforms                        │
│  sensor.py  │  button.py  │  switch.py           │
│  8 sensors  │  6 buttons  │  2 switches          │
│  Status + queue list, counts, approval, targets  │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│           Services                               │
│  (services.yaml + __init__.py)                   │
│  10 service actions for automation/scripting     │
└─────────────────────────────────────────────────┘
```

### Data Flow

1. **Discovery** — Entity registry is scanned for `update.*` entities
2. **Classification** — Entities are mapped to groups via `INTEGRATION_GROUP_MAP`
3. **Filtering** — Entities are filtered by group mode (disabled → skip), exclusions, battery status
4. **Queueing** — Eligible entities are added as `QueueItem` objects, sorted by group execution order
5. **Approval** — Items in `manual_only` groups are set to `waiting_approval` status
6. **Execution** — Groups are processed in order:
   - Sequential: one at a time, wait for each
   - Parallel: all at once (with safety overrides for Z-Wave, HA Core/OS)
   - Manual_only: only process approved items
7. **Persistence** — Queue state saved to `Store` after each change

---

## Update Groups

| Group Key | Display Name | Default Mode | Safety Override |
|-----------|-------------|-------------|----------------|
| `zwave` | Z-Wave Firmware | sequential | **Always sequential** |
| `esphome` | ESPHome Devices | sequential | — |
| `hacs` | HACS Integrations | disabled | — |
| `ha_core` | Home Assistant Core | disabled | **Always sequential** |
| `ha_os` | Home Assistant OS | disabled | **Always sequential** |
| `addons` | Add-ons | manual_only | — |
| `matter` | Matter Devices | sequential | — |
| `mqtt` | MQTT Devices | sequential | — |
| `other` | Other Updates | manual_only | — |

### Integration-to-Group Mapping

| HA Platform | Group |
|------------|-------|
| `zwave_js` | zwave |
| `zwave` | zwave |
| `esphome` | esphome |
| `hacs` | hacs |
| `homeassistant` | ha_core |
| `hassio` | ha_os |
| `hassio_addons` | addons |
| `update` | ha_core |
| `matter` | matter |
| `mqtt` | mqtt |
| *(anything else)* | other |

### Group Execution Order

Device firmware is processed first, system updates last:

1. Z-Wave Firmware
2. ESPHome Devices
3. Matter Devices
4. MQTT Devices
5. Other Updates
6. Add-ons
7. HACS Integrations
8. Home Assistant Core
9. Home Assistant OS

---

## Configuration Schema

### Initial Setup (Config Flow)

No configuration fields — just click Submit to create the entry. All settings are configured in the Options flow.

### Options Flow — Step 1: Global Settings

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `auto_start` | bool | `false` | — | Auto-start queue on refresh |
| `zwave_mains_only` | bool | `true` | — | Skip battery Z-Wave devices |
| `install_delay` | int | `15` | 0–300 | Seconds between installs |
| `install_timeout` | int | `7200` | 60–14400 | Seconds per update timeout |
| `max_retries` | int | `2` | 0–10 | Retries per failed update |
| `stop_on_failure` | bool | `false` | — | Stop queue on first failure |
| `skip_unavailable` | bool | `true` | — | Skip unavailable entities |
| `maintenance_window_enabled` | bool | `false` | — | Enable time window |
| `maintenance_window_start` | string | `02:00` | HH:MM | Window start time |
| `maintenance_window_end` | string | `05:00` | HH:MM | Window end time |

### Options Flow — Step 2: Per-Group Execution Modes

| Field | Type | Default | Options |
|-------|------|---------|---------|
| `mode_zwave` | select | `sequential` | sequential, parallel, disabled, manual_only |
| `mode_esphome` | select | `sequential` | sequential, parallel, disabled, manual_only |
| `mode_hacs` | select | `disabled` | sequential, parallel, disabled, manual_only |
| `mode_ha_core` | select | `disabled` | sequential, parallel, disabled, manual_only |
| `mode_ha_os` | select | `disabled` | sequential, parallel, disabled, manual_only |
| `mode_addons` | select | `manual_only` | sequential, parallel, disabled, manual_only |
| `mode_matter` | select | `sequential` | sequential, parallel, disabled, manual_only |
| `mode_mqtt` | select | `sequential` | sequential, parallel, disabled, manual_only |
| `mode_other` | select | `manual_only` | sequential, parallel, disabled, manual_only |

### Options Flow — Step 3: Exclusion Filters

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `exclude_entities` | string | `""` | Comma-separated entity IDs to skip |
| `exclude_areas` | string | `""` | Comma-separated area IDs to skip |
| `exclude_labels` | string | `""` | Comma-separated labels to skip |

---

## Queue Manager

### QueueItem States

```
pending ──────────→ installing → completed
                                → failed (retries exhausted)
                                → skipped (user skip or unavailable)

waiting_approval → approved → installing → completed / failed / skipped
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
for entity in entity_registry:
    if not entity.startswith("update."):  skip
    if entity.disabled:                   skip
    if entity in exclude_entities:        skip
    if entity.area in exclude_areas:      skip
    if entity.labels & exclude_labels:    skip
    if state != "on":                     skip  # no update available
    if skip_unavailable and state == "unavailable":  skip

    group = INTEGRATION_GROUP_MAP.get(entity.platform, "other")
    mode = get_group_mode(group)

    if mode == "disabled":                skip
    if group == "zwave" and mains_only:
        if is_battery_device(entity):     skip

    if mode == "manual_only":
        item.status = "waiting_approval"
    else:
        item.status = "pending"

    add to queue, sorted by GROUP_EXECUTION_ORDER
```

### Install Logic

```python
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

### Safety Overrides

These overrides cannot be disabled and apply even when the user selects "parallel":

1. **Z-Wave** — Always forced to sequential. Z-Wave firmware updates must complete one at a time to avoid Z-Wave mesh contention.
2. **HA Core** — Always forced to sequential. Core updates restart HA and would interrupt other updates.
3. **HA OS** — Always forced to sequential. OS updates reboot the machine.

---

## Services API

### sh_update_manager.start_queue
- **Parameters:** none
- **Effect:** Discovers updates, groups them, starts processing by group in execution order

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
- **Effect:** Rescans entity registry, classifies entities into groups, updates queue

### sh_update_manager.install_all_eligible
- **Parameters:** none
- **Effect:** Same as start_queue (discover + group + install)

### sh_update_manager.install_entity
- **Parameters:**
  - `entity_id` (required): Target update entity (e.g., `update.kitchen_light_firmware`)
- **Effect:** Immediately installs the specified update (bypasses queue)

### sh_update_manager.approve_item
- **Parameters:**
  - `entity_id` (required): Target update entity waiting for approval
- **Effect:** Changes item status from `waiting_approval` to `approved`

### sh_update_manager.clear_queue
- **Parameters:** none
- **Effect:** Clears all items from the queue and resets completed/failed counters

---

## Entity Specifications

### Sensors (8)

| Entity ID | Name | Unit | Value | Extra Attributes |
|-----------|------|------|-------|-----------------|
| `sensor.*_queue_status` | Queue Status | — | idle/running/paused/stopped | total_in_queue, pending, waiting_approval, installing, completed, failed, skipped, queue_items (full list) |
| `sensor.*_pending_updates` | Pending Updates | updates | int | — |
| `sensor.*_waiting_approval` | Waiting Approval | updates | int | items (list of waiting entities) |
| `sensor.*_current_update` | Current Update Target | — | entity_id or None | group, friendly_name, versions, retries |
| `sensor.*_last_success` | Last Success | — | entity_id or None | — |
| `sensor.*_last_failure` | Last Failure | — | entity_id or None | — |
| `sensor.*_completed_count` | Completed Updates | updates | int | — |
| `sensor.*_failed_count` | Failed Updates | updates | int | — |

### Buttons (6)

| Entity ID | Name | Effect |
|-----------|------|--------|
| `button.*_update_all_eligible` | Update All Eligible | Starts the queue |
| `button.*_refresh_candidates` | Refresh Update Scan | Rescans updates |
| `button.*_stop_queue` | Stop Queue | Stops queue |
| `button.*_skip_current` | Skip Current Update | Skips current |
| `button.*_approve_all` | Approve All Waiting | Approves all manual-only items |
| `button.*_clear_queue` | Clear Queue | Clears queue and resets counters |

### Switches (2)

| Entity ID | Name | Effect |
|-----------|------|--------|
| `switch.*_auto_start` | Auto Start Queue | Toggles auto-start mode |
| `switch.*_pause_queue` | Pause Queue | Toggles pause |

---

## Persistence

Queue state is persisted using Home Assistant's `Store` API:

- **Storage key:** `sh_update_manager.queue`
- **Storage version:** 2
- **Persisted data:**
  - Queue items (entity_id, group, status, retries, timestamps, friendly_name, versions, error)
  - Queue state (idle/running/paused/stopped)
  - Counters (completed, failed)
  - Last success/failure entity IDs

This ensures the queue survives Home Assistant restarts.

---

## Future Enhancements

### v1.2 (Planned)
- [ ] Notification service calls (before/after updates, on failure)
- [ ] Detailed update history log entity
- [ ] Custom Lovelace card for queue visualization

### v2.0 (Future)
- [ ] Dashboard panel with drag-and-drop queue ordering
- [ ] Protocol-specific adapters (Z-Wave wake-up handling)
- [ ] Backup-before-update integration
- [ ] Rollback support (where the update platform supports it)
- [ ] Multi-instance support for different rule sets

---

## Version History

### v1.1.0 — 2026-04-08
- Per-group execution modes (sequential, parallel, disabled, manual_only)
- 9 update groups with integration-to-group mapping
- Z-Wave always-sequential safety override
- HA Core/OS always-sequential safety override
- Manual approval workflow for manual_only groups
- Group execution order (device firmware first, system last)
- Multi-step options flow (global → per-group → filters)
- Full queue list in sensor attributes with group info
- Waiting Approval sensor
- Approve All and Clear Queue buttons
- 2 new services: approve_item, clear_queue
- 8 sensors, 6 buttons, 2 switches
- 10 services total

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
