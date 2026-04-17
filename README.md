# Smarter.Homes Update Manager

**by Smarter Homes LLC — [smarter.homes](https://smarter.homes)**

A Home Assistant custom integration for managing device updates with named queues, per-device tracking, battery handling, retry logic, and a dedicated sidebar panel.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

## Screenshots

### Queue Management Panel
![Queue List](docs/images/update_manager_queues.png)
*Sidebar panel showing all queues with status, settings, and per-queue controls (Scan, Start, History)*

### Add New Queue
![Add Queue Form](docs/images/update_manager_add_queue.png)
*Create a new queue with match type, match values, exclude patterns, execution mode, trigger mode, battery handling, and priority*

### Advanced Filtering — Device Name
![Device Name Filter](docs/images/update_manager_device_name_filter.png)
*Filter by device name (e.g. "Zooz" to match all Zooz Z-Wave devices) with context-sensitive placeholder text*

### Edit Queue
![Edit Queue](docs/images/update_manager_edit_queue.png)
*Edit existing queue settings — all fields are pre-filled with current values*

## Features

### Device-Per-Queue Architecture
Each queue you create becomes its own HA device with dedicated sensors, buttons, and switches. No more mixed entities — everything is cleanly separated.

### Named Queues
Create queues like "Z-Wave Firmware", "ESPHome Devices", "HACS Updates" — each with independent configuration:
- **Match rules**: Filter by integration, area, label, entity, device name, or manufacturer
- **Execution mode**: Sequential (one-at-a-time) or parallel
- **Trigger mode**: Manual or auto-on-scan
- **Priority**: 1-100 (lower = runs first when using Start All)

### Battery Device Handling
- **Exclude** (default): Battery devices are skipped entirely
- **Defer to end**: Battery devices are moved to the end of the queue so they don't block mains-powered updates
- **Include**: Battery devices are mixed in normally

### Update History & Results
Every queue run is logged with:
- Start/end time and duration
- Succeeded/failed/skipped counts
- Failed item details with error messages
- Configurable history depth (default: 25 runs)

### Retry Failed
One-click retry for all failed items in a queue. Failed items are re-queued and the queue restarts automatically.

### Safety Overrides
- **Z-Wave**: Always forced sequential regardless of config (firmware updates must be one-at-a-time)
- **HA Core / HA OS / Supervisor**: Separated into their own "Core Updates" queue (priority 5) so they never mix with regular add-on updates. The Add-ons queue auto-excludes core entities.

### Sidebar Panel
Dedicated management UI accessible from the HA sidebar — the **central hub** for all queue management:
- **Add Queue** button to create new queues with a form dialog
- **Edit** and **Delete** buttons on each queue card
- Form dialogs with friendly dropdowns for all settings (match type, exec mode, trigger mode, battery handling, priority)
- **Exclude Pattern** field to exclude specific devices (e.g. exclude ZEN32 from a Z-Wave queue)
- Context-sensitive placeholder text that changes based on selected match type
- Advanced settings collapsible section (install delay, timeout, retries, history count)
- Delete confirmation dialog
- Visual queue overview with real-time status
- Per-queue controls (scan, start, stop, pause, resume, skip, retry)
- Queue items with version details and battery indicators
- Run history browser
- No need to navigate to Settings — everything is managed from the panel

### HA Native Scheduling
No custom scheduler — use HA's built-in automations and schedule helpers to trigger queues on your schedule.

## Installation

### HACS (Recommended)
1. Open HACS → Integrations → 3-dot menu → Custom repositories
2. Add: `https://github.com/csmadeit/ha-sh-update-manager`
3. Category: Integration
4. Install "Smarter.Homes Update Manager" → Restart HA

### Manual
1. Download the latest release from [GitHub Releases](https://github.com/csmadeit/ha-sh-update-manager/releases)
2. Copy `custom_components/sh_update_manager/` to your HA `custom_components/` directory
3. Restart HA

## Setup

1. **Settings → Devices & Services → Add Integration → Smarter.Homes Update Manager**
2. Select which default queues to create (or deselect all and add your own later)
3. Open the **Update Manager** sidebar panel to add/edit/delete queues and manage updates

## Entities Per Queue

Each queue device has **12 entities**:

| Type | Entity | Description |
|------|--------|-------------|
| Sensor | Status | Queue state (idle/running/paused/stopped) |
| Sensor | Pending Updates | Count of pending items with battery breakdown |
| Sensor | Queue Items | Full item list with details in attributes |
| Sensor | Last Run Result | Result of most recent run |
| Sensor | Update History | Run history with all details |
| Button | Scan | Discover pending updates for this queue |
| Button | Start | Begin processing the queue |
| Button | Stop | Stop the queue immediately |
| Button | Skip Current | Skip the item currently installing |
| Button | Retry Failed | Re-queue failed items and restart |
| Switch | Pause | Pause/resume the queue |
| Switch | Auto-trigger | Toggle auto-start on scan |

### Hub Device (5 entities)
| Type | Entity | Description |
|------|--------|-------------|
| Sensor | Overview | Global status across all queues |
| Button | Scan All Queues | Scan every queue for updates |
| Button | Start All Queues | Start all queues by priority |
| Button | Stop All Queues | Stop all running queues |
| Switch | Pause All | Pause/resume all queues |

## Services

| Service | Description |
|---------|-------------|
| `sh_update_manager.scan_all` | Scan all queues for pending updates |
| `sh_update_manager.start_queue` | Start a queue by name |
| `sh_update_manager.stop_queue` | Stop a queue by name |
| `sh_update_manager.pause_queue` | Pause a running queue |
| `sh_update_manager.resume_queue` | Resume a paused queue |
| `sh_update_manager.skip_current` | Skip the current item in a queue |
| `sh_update_manager.clear_queue` | Clear all items from a queue |
| `sh_update_manager.retry_failed` | Retry all failed items in a queue |
| `sh_update_manager.scan_queue` | Scan a single queue |
| `sh_update_manager.add_queue` | Create a new queue |
| `sh_update_manager.edit_queue` | Edit an existing queue |
| `sh_update_manager.delete_queue` | Delete a queue |

## Automation Example

```yaml
automation:
  - alias: "Weekly Z-Wave Firmware Update"
    trigger:
      - platform: time
        at: "03:00:00"
    condition:
      - condition: time
        weekday: [sun]
    action:
      - service: sh_update_manager.scan_queue
        data:
          queue_name: "Z-Wave Firmware"
      - delay: "00:00:30"
      - service: sh_update_manager.start_queue
        data:
          queue_name: "Z-Wave Firmware"
```

## Queue Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| name | — | Queue display name |
| match_type | integration | How to match entities: integration, area, label, entity, device_name, manufacturer |
| match_value | — | Comma-separated match values |
| exclude_pattern | — | Comma-separated patterns to exclude (matched against device name, manufacturer, model, entity ID) |
| exec_mode | sequential | sequential or parallel |
| trigger_mode | manual | manual or auto_on_scan |
| battery_handling | exclude | exclude, defer_to_end, or include |
| stop_on_failure | false | Stop queue if an update fails |
| skip_unavailable | true | Skip unavailable devices |
| install_delay | 5 | Seconds between installs (0-300) |
| install_timeout | 600 | Max seconds to wait per install (60-14400) |
| max_retries | 1 | Retry attempts per device (0-10) |
| history_count | 25 | Number of past runs to keep (1-100) |
| priority | 50 | Queue priority for Start All (1-100, lower = first) |

## Version History

| Version | Changes |
|---------|---------|
| 2.1.3 | Hotfix for v2.1.2: `async_setup_entry` called `_reschedule_auto_scan` but the function + its `timedelta` / `async_track_time_interval` imports were missing from `__init__.py`, causing `NameError` on setup ("Error setting up entry Smarter.Homes Update Manager for sh_update_manager"). 2.1.2 was unusable — upgrade directly from 2.1.1 to 2.1.3. Scheduled scans, queue_5 label fix, and "Why skipped?" diagnostics from 2.1.2 are all in. |
| 2.1.2 | Fixes and diagnostics: (1) Setup wizard no longer renders a 6th unnamed "queue_5" checkbox — labels in `strings.json` are now aligned with `DEFAULT_QUEUES` order (queue_0 = Core Updates, queue_5 = Other Updates). (2) New **auto-scan interval** under Options → Global settings (minutes; 0 = disabled). When enabled, the integration runs `scan_all` on a fixed interval so new updates show up without clicking Scan. (3) New per-queue **"Why skipped?"** panel in the sidebar exposes exactly why each matching update entity was dropped during the last scan (disabled, unavailable, up-to-date, battery excluded, exclude pattern, etc.) — makes it obvious when e.g. a Z-Wave sensor is skipped because the queue's `battery_handling` is `exclude`. Change the queue's Battery setting to `defer_to_end` or `include` to pick up battery devices. |
| 2.1.1 | Fix: Scan/Scan All no longer appear to "do nothing" when a previously-completed update entity has a new release. Completed/failed/skipped items are automatically re-queued to `pending` when a newer installed/latest version is detected on the same entity, and pending items have their version/display info refreshed on every scan. |
| 2.1.0 | Separate core updates (HA Core, HA OS, Supervisor) from add-on updates into dedicated "Core Updates" queue; existing installs auto-migrate |
| 2.0.3 | Rename to Smarter.Homes branding, queue management UI in sidebar panel (Add/Edit/Delete), advanced filtering (device name, manufacturer match types, exclude patterns), comprehensive USAGE.md manual, cache-busting panel versioning |
| 2.0.2 | Fix setup failure on production HA: config entry migration handler, robust error handling, Platform enum, remove entry_type from device_info |
| 2.0.1 | Fix HA 2024.1.0 compatibility: robust panel registration with version fallbacks, remove frontend dependency |
| 2.0.0 | Complete redesign: device-per-queue, sidebar panel, update history, battery handling, retry failed, priorities |
| 1.2.2 | Queue selection improvements |
| 1.2.1 | Setup flow with queue checkboxes |
| 1.2.0 | Queue-based architecture |
| 1.1.0 | Per-group rules, Z-Wave sequential, HA/HAOS exclusion |
| 1.0.0 | Initial release — basic sequential queue |

## License

MIT

## Credits

Built by [Smarter Homes LLC](https://smarter.homes) — Making home automation smarter.
