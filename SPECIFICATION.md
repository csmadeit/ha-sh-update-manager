# Smarter.Homes Update Manager — Specification v2.1.4

**by Smarter Homes LLC — smarter.homes**

## Overview

Smarter.Homes Update Manager is a Home Assistant custom integration that provides queue-based management of HA update entities. Each queue registers as a separate HA device, enabling clean separation of concerns and native automation support.

## Architecture

### Two-Layer Design

**Layer A: Queue Devices (Monitoring + Control + Automation)**
- Each queue = its own HA device with sensors, buttons, switches
- Hub device for global overview and controls
- Native HA automations can trigger any queue entity

**Layer B: Management UI (Configuration)**
- Sidebar panel (LitElement/JS) — central hub for all queue management
- Add/Edit/Delete queue forms with dropdown selectors directly in the panel
- Config flow options as fallback for queue CRUD
- Real-time status display with auto-refresh

### Storage

- **Config entry**: Queue configurations (names, match rules, settings)
- **Store file** (`sh_update_manager.json`): Runtime state, queue items, run history
- **Storage version**: 4

## Data Model

### QueueItem
```
entity_id: str          # update.* entity
group: str              # integration group (zwave_js, esphome, etc.)
retries: int            # current retry count
status: str             # pending | installing | completed | failed | skipped
error: str | None       # error message if failed
started_at: datetime    # when install started
completed_at: datetime  # when install finished
friendly_name: str      # human-readable name
installed_version: str  # version before update
latest_version: str     # version being installed
is_battery: bool        # whether device is battery-powered
duration: str           # human-readable duration
```

### RunRecord
```
run_id: int             # sequential run counter
started: datetime       # run start time
ended: datetime         # run end time
total: int              # total items in run
succeeded: int          # successful installs
failed: int             # failed installs
skipped: int            # skipped items
result: str             # idle | completed | completed_with_failures | failed
failed_items: list      # details of failed items
succeeded_items: list   # details of succeeded items
```

### NamedQueue Configuration
```
name: str                    # display name
match_type: str              # integration | area | label | entity | device_name | manufacturer
match_value: str             # comma-separated values
exclude_pattern: str         # comma-separated exclude patterns (matched against device name, manufacturer, model, entity ID)
exec_mode: str               # sequential | parallel
trigger_mode: str            # manual | auto_on_scan
battery_handling: str        # exclude | defer_to_end | include
stop_on_failure: bool        # stop queue on first failure
skip_unavailable: bool       # skip unavailable entities
install_delay: int           # seconds between installs (0-300)
install_timeout: int         # max seconds per install (60-14400)
max_retries: int             # retry attempts (0-10)
history_count: int           # runs to keep (1-100)
priority: int                # queue priority (1-100, lower = first)
```

## Entity Specification

### Hub Device: "Smarter.Homes Update Manager"
| Platform | Entity ID Pattern | Description |
|----------|-------------------|-------------|
| sensor | `sensor.sh_update_manager_overview` | Global queue overview |
| button | `button.sh_update_manager_scan_all_queues` | Scan all queues |
| button | `button.sh_update_manager_start_all_queues` | Start all by priority |
| button | `button.sh_update_manager_stop_all_queues` | Stop all running |
| switch | `switch.sh_update_manager_pause_all` | Pause/resume all |

### Per-Queue Device: "Update Queue: {name}"
| Platform | Entity ID Pattern | Description |
|----------|-------------------|-------------|
| sensor | `sensor.update_queue_{slug}_status` | Queue state |
| sensor | `sensor.update_queue_{slug}_pending_updates` | Pending count + summary |
| sensor | `sensor.update_queue_{slug}_queue_items` | Full item list |
| sensor | `sensor.update_queue_{slug}_last_run_result` | Latest run result |
| sensor | `sensor.update_queue_{slug}_update_history` | Run history |
| button | `button.update_queue_{slug}_scan` | Scan for updates |
| button | `button.update_queue_{slug}_start` | Start queue |
| button | `button.update_queue_{slug}_stop` | Stop queue |
| button | `button.update_queue_{slug}_skip_current` | Skip current item |
| button | `button.update_queue_{slug}_retry_failed` | Retry failed items |
| switch | `switch.update_queue_{slug}_pause` | Pause/resume |
| switch | `switch.update_queue_{slug}_auto_trigger` | Auto-start on scan |

## Service Specification

### scan_all
- **Domain**: sh_update_manager
- **Fields**: None
- **Behavior**: Scans all queues for pending updates. Queues with `trigger_mode: auto_on_scan` will auto-start if updates found.

### start_queue
- **Domain**: sh_update_manager
- **Fields**: `queue_name` (string, required)
- **Behavior**: Scans the queue first, then starts processing. Sequential queues process one item at a time with `install_delay` between each. Parallel queues process all items concurrently.

### stop_queue / pause_queue / resume_queue
- **Domain**: sh_update_manager
- **Fields**: `queue_name` (string, required)
- **Behavior**: Stop cancels the running task. Pause sets state to paused (processing loop waits). Resume continues from where it paused.

### skip_current
- **Domain**: sh_update_manager
- **Fields**: `queue_name` (string, required)
- **Behavior**: Marks the current item as skipped and moves to the next one.

### retry_failed
- **Domain**: sh_update_manager
- **Fields**: `queue_name` (string, required)
- **Behavior**: Resets all failed items to pending, clears their error/retry counts, then starts the queue.

### scan_queue
- **Domain**: sh_update_manager
- **Fields**: `queue_name` (string, required)
- **Behavior**: Scans a single queue for pending updates without starting it. Logs detailed breakdown of skipped entities (disabled, no-match, not-on, unavailable, battery-excluded).
- **Re-queue semantics (v2.1.1+)**: If an update entity that was previously completed/failed/skipped reports a new installed/latest version pair (i.e. a fresh release landed for the same entity), the scan resets that item back to `pending` and refreshes its version/display attributes. This fixes the previous behavior where the Scan button appeared to "do nothing" after an entity cycled through an install and then had another release published.

### add_queue
- **Domain**: sh_update_manager
- **Fields**: `queue_name` (required), `match_type`, `match_value`, `exec_mode`, `trigger_mode`, `battery_handling`, `stop_on_failure`, `skip_unavailable`, `install_delay`, `install_timeout`, `max_retries`, `history_count`, `priority`
- **Behavior**: Creates a new queue with given configuration, persists to config entry, and saves to store.

### edit_queue
- **Domain**: sh_update_manager
- **Fields**: `queue_name` (required), `new_name` (optional), plus any config fields to update
- **Behavior**: Updates the specified queue's configuration. Supports renaming via `new_name`. Persists changes.

### delete_queue
- **Domain**: sh_update_manager
- **Fields**: `queue_name` (required)
- **Behavior**: Removes the queue and persists the change. Queue devices/entities are removed on next reload.

## Match Types

| Match Type | Match Behavior | Example Values |
|------------|---------------|----------------|
| integration | Entity platform equals value | `zwave_js`, `esphome`, `hacs` |
| area | Entity area ID equals value | `living_room`, `office` |
| label | Entity label intersects values | `critical`, `firmware` |
| entity | Entity ID equals value | `update.zooz_zen71_firmware` |
| device_name | Partial match against device name + model (case-insensitive) | `Zooz`, `ZEN71` |
| manufacturer | Exact match against device manufacturer (case-insensitive) | `Zooz`, `Inovelli` |

### Exclude Patterns

The `exclude_pattern` field allows comma-separated patterns that are matched case-insensitively against:
- Device name
- Manufacturer
- Model
- Entity ID
- Friendly name

If any pattern matches any of these fields, the entity is excluded from the queue even if it matches the main filter.

**Example:** Match type `integration = zwave_js` with exclude pattern `ZEN32` → all Z-Wave updates except ZEN32 devices.

## Safety Overrides

### Z-Wave Sequential Enforcement
Any queue matching `zwave_js` integration is forced to sequential mode regardless of `exec_mode` config. Z-Wave firmware updates must complete one-at-a-time to avoid radio conflicts.

### HA Core / HA OS Exclusion
Default queues do not include `homeassistant` or `hassio` integrations. Users must explicitly create a queue matching these integrations if they want managed HA updates.

## Battery Device Detection

Battery detection checks the device registry for:
1. Any entity with `device_class: battery` on the same device
2. Any entity with "battery" in the entity_id on the same device

Battery handling modes:
- **exclude**: Battery devices are not added to the queue
- **defer_to_end**: Battery devices are sorted to the end of pending items
- **include**: Battery devices are mixed in with mains-powered devices normally

## Sidebar Panel

### Registration
- Component: `custom` panel via `async_register_built_in_panel`
- Static path: `/sh_update_manager/frontend/` serving panel.js
- URL: `/sh-update-manager`
- Icon: `mdi:update`

### Features
- **Queue Management**: Add, Edit, Delete queues directly from the panel
- Modal form dialogs with dropdown selectors for match_type, exec_mode, trigger_mode, battery_handling
- Exclude pattern field for filtering out specific devices from matched results
- Context-sensitive placeholder text for match values based on selected match type
- Advanced settings collapsible section (install_delay, install_timeout, max_retries, history_count)
- Delete confirmation dialog
- Real-time queue grid with auto-refresh (5-second polling)
- Per-queue controls (scan, start, stop, pause, resume, skip, retry)
- Item list with version details and battery badges
- Run history browser per queue
- Responsive grid layout
- Page auto-reloads after Add/Edit/Delete to pick up config changes

## Config Flow

### Initial Setup
1. Shows checkboxes for 5 default queues
2. User selects which to create (at least one required)
3. Creates config entry with selected queues

### Options Flow
1. **Init step**: Dropdown with actions: Add / Edit / Delete per queue / Save
2. **Add queue**: Full form with all configuration options
3. **Edit queue**: Pre-populated form with current values
4. **Delete queue**: Removes queue from list

## Default Queues

| Name | Match | Exec Mode | Battery |
|------|-------|-----------|---------|
| Z-Wave Firmware | zwave_js | sequential (forced) | exclude |
| ESPHome Devices | esphome | sequential | exclude |
| HACS Updates | hacs | sequential | exclude |
| Add-ons | hassio | sequential | exclude |
| Other Updates | mqtt, matter | sequential | exclude |

## File Structure

```
custom_components/sh_update_manager/
├── __init__.py          # Integration setup, services, panel registration
├── const.py             # Constants, defaults, config keys
├── queue_manager.py     # QueueItem, RunRecord, NamedQueue, QueueCoordinator
├── sensor.py            # Hub + per-queue sensors
├── button.py            # Hub + per-queue buttons
├── switch.py            # Hub + per-queue switches
├── config_flow.py       # Setup + options flow with queue CRUD
├── manifest.json        # Integration manifest (v2.1.3)
├── services.yaml        # Service definitions
├── strings.json         # UI strings
├── translations/
│   └── en.json          # English translations
└── frontend/
    └── panel.js         # LitElement sidebar panel
```

## Future Enhancements

- Dashboard card (Lovelace custom card for embedding queue views)
- Notification integration (alerts on failure, completion summaries)
- Queue dependencies (queue B waits for queue A to complete)
- Import/export queue configurations
- Update changelogs in history (pull release notes from integrations)
