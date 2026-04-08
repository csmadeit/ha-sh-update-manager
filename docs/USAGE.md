# Smarter.Homes Update Manager — User Manual

A comprehensive guide to installing, configuring, and using the
Smarter.Homes Update Manager for Home Assistant.

by Smarter Homes LLC — [smarter.homes](https://smarter.homes)

---

## Table of Contents

1. [Installation](#installation)
2. [First-Time Setup](#first-time-setup)
3. [The Sidebar Panel](#the-sidebar-panel)
4. [Creating Queues](#creating-queues)
5. [Match Types & Filtering](#match-types--filtering)
6. [Exclude Patterns](#exclude-patterns)
7. [Battery Device Handling](#battery-device-handling)
8. [Running Updates](#running-updates)
9. [Queue History & Results](#queue-history--results)
10. [Automations & Scheduling](#automations--scheduling)
11. [Services Reference](#services-reference)
12. [Troubleshooting](#troubleshooting)

---

## Installation

### Via HACS (Recommended)

1. Open **HACS** in your Home Assistant instance.
2. Go to **Integrations** → three-dot menu → **Custom repositories**.
3. Add URL: `https://github.com/csmadeit/ha-sh-update-manager`
4. Category: **Integration**
5. Click **Add**, then install **Smarter.Homes Update Manager**.
6. Restart Home Assistant.

### Manual Installation

1. Download the latest release from
   [GitHub Releases](https://github.com/csmadeit/ha-sh-update-manager/releases).
2. Copy the `custom_components/sh_update_manager` folder into your
   `config/custom_components/` directory.
3. Restart Home Assistant.

---

## First-Time Setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Smarter.Homes Update Manager**.
3. Follow the setup wizard — you can choose which default queues to create
   or skip them all and build your own from scratch.
4. After setup, the **Update Manager** sidebar panel appears automatically.

---

## The Sidebar Panel

The sidebar panel is your central hub for managing update queues. Access it
by clicking **Update Manager** in the left sidebar.

### What You See

- **Header actions:** Add Queue, Scan All Queues, Stop All, Refresh
- **Queue cards:** One card per queue showing status, settings, pending
  updates, and action buttons
- **Queue actions:** Scan, Start, Stop, Pause, Resume, Skip Current,
  Retry Failed, Clear
- **Edit/Delete:** Each queue card has Edit and Delete buttons

### Queue Card Details

Each queue card shows:

| Field | Description |
|-------|-------------|
| **Priority** | 1-100 (lower = runs first) |
| **Mode** | Sequential or parallel execution |
| **Trigger** | Manual or auto-on-scan |
| **Battery** | How battery devices are handled |
| **Match** | Which devices are included (and excluded) |
| **Pending** | Number of pending updates with device names |
| **Last Run** | Result of the most recent run |

---

## Creating Queues

Click **"+ Add Queue"** in the sidebar panel to create a new queue.

### Required Fields

- **Queue Name** — A descriptive name (e.g., "Z-Wave Firmware",
  "All Zooz Devices", "ESPHome OTA")

### Match Settings

- **Match Type** — How to find update entities for this queue
- **Match Values** — Comma-separated values to match
- **Exclude Pattern** — Optional patterns to exclude (see below)

### Execution Settings

- **Execution Mode** — Sequential (one at a time) or Parallel (all at once)
- **Trigger Mode** — Manual (press Start) or Auto on Scan
- **Battery Handling** — Exclude, defer to end, or include
- **Priority** — 1-100, lower number = higher priority

### Advanced Settings (expand "Advanced Settings")

- **Install Delay** — Seconds between each install (0-300)
- **Install Timeout** — Max wait per device (60-14400 seconds)
- **Max Retries** — Retry attempts for failed installs (0-10)
- **History Count** — Past runs to keep per queue (1-100)

---

## Match Types & Filtering

The **Match Type** determines how a queue finds update entities.

### Integration (default)

Match by Home Assistant integration platform name.

| Example Values | What It Matches |
|----------------|-----------------|
| `zwave_js` | All Z-Wave JS update entities |
| `zwave_js,zwave` | Z-Wave JS and legacy Z-Wave |
| `esphome` | All ESPHome device updates |
| `hacs` | All HACS integration updates |
| `hassio_addons,hassio` | Add-ons and HA OS |

### Area

Match by Home Assistant area ID.

| Example Values | What It Matches |
|----------------|-----------------|
| `living_room` | All updates in "Living Room" area |
| `office,bedroom` | Updates in Office or Bedroom |

### Label

Match by entity labels (HA 2024.x+).

| Example Values | What It Matches |
|----------------|-----------------|
| `critical` | All updates with "critical" label |
| `firmware,ota` | Updates with "firmware" or "ota" label |

### Entity

Match specific entity IDs directly.

| Example Values | What It Matches |
|----------------|-----------------|
| `update.zooz_zen71_firmware` | Only that one entity |
| `update.zooz_zen71_firmware,update.zooz_zen76_firmware` | Those two entities |

### Device Name (v2.0.3+)

Match by device name and/or model. **Partial, case-insensitive match** —
the value is searched within the device name and model fields.

| Example Values | What It Matches |
|----------------|-----------------|
| `Zooz` | All devices with "Zooz" in name or model |
| `ZEN71` | All devices with "ZEN71" in name or model |
| `Zooz,Inovelli` | All Zooz OR Inovelli devices |

This is perfect for creating vendor-specific queues like "All Zooz Z-Wave
devices" without knowing every integration platform name.

### Manufacturer (v2.0.3+)

Match by the device's manufacturer field. **Exact, case-insensitive match.**

| Example Values | What It Matches |
|----------------|-----------------|
| `Zooz` | All devices from manufacturer "Zooz" |
| `Zooz,Inovelli` | Devices from Zooz or Inovelli |

---

## Exclude Patterns

The **Exclude Pattern** field (v2.0.3+) lets you remove specific devices
from a queue, even if they match the main filter. Patterns are:

- **Comma-separated** — multiple patterns separated by commas
- **Case-insensitive** — "zen32" matches "ZEN32"
- **Partial match** — checked against device name, manufacturer, model,
  entity ID, and friendly name

### Examples

| Queue Setup | Result |
|-------------|--------|
| Match: `integration = zwave_js` / Exclude: `ZEN32` | All Z-Wave updates EXCEPT ZEN32 devices |
| Match: `manufacturer = Zooz` / Exclude: `ZEN32,ZEN17` | All Zooz devices except ZEN32 and ZEN17 |
| Match: `device_name = Zooz` / Exclude: `button controller` | All Zooz devices except button controllers |

### Use Cases

- **Skip problematic devices:** Exclude devices that consistently fail
  updates (e.g., `ZEN32` if its firmware update is unreliable)
- **Separate battery from mains:** Use the Battery Handling setting, or
  manually exclude battery device names
- **Vendor subset:** Match all Zooz, exclude specific models you want to
  handle separately

---

## Battery Device Handling

Each queue has a Battery Handling setting:

| Option | Behavior |
|--------|----------|
| **Exclude** (default) | Battery-powered devices are skipped entirely |
| **Defer to End** | Battery devices are included but placed at the end of the queue |
| **Include** | Battery devices are mixed in with mains-powered devices |

**Why exclude by default?** Battery-powered Z-Wave devices are often
asleep and can block the queue waiting for them to wake up. Deferring to
the end ensures mains-powered devices are updated first without delays.

---

## Running Updates

### Manual Start (Recommended)

1. Click **Scan** on a queue to discover pending updates.
2. Review the pending list — you'll see device names, current and available
   versions.
3. Click **Start** to begin processing.
4. Watch progress in real-time — the current item shows "installing" status.

### Scan All Queues

Click **"Scan All Queues"** in the header to refresh all queues at once.

### During a Run

- **Pause** — Temporarily halt after the current item finishes.
- **Resume** — Continue a paused queue.
- **Stop** — Cancel the run entirely.
- **Skip Current** — Skip the currently installing item and move to the
  next one.

### After a Run

- Check **Last Run** result: `completed`, `completed_with_failures`, or
  `failed`.
- Click on a queue to see the full history with details.
- Use **Retry Failed** to re-queue any failed items and try again.

---

## Queue History & Results

Each queue maintains a history of past runs (configurable, default 25).

Each run record includes:
- Start and end time
- Total items processed
- Succeeded / Failed / Skipped counts
- List of failed items with error details
- List of succeeded items

Click the History button on a queue card to view past runs.

---

## Automations & Scheduling

The integration exposes services you can call from HA automations, scripts,
and the built-in Schedule helper.

### Example: Nightly Z-Wave Update at 3 AM

```yaml
automation:
  - alias: "Nightly Z-Wave Firmware Update"
    trigger:
      - platform: time
        at: "03:00:00"
    action:
      - service: sh_update_manager.scan_queue
        data:
          queue_name: "Z-Wave Firmware"
      - delay: "00:00:10"
      - service: sh_update_manager.start_queue
        data:
          queue_name: "Z-Wave Firmware"
```

### Example: Weekly Full Scan + Start All

```yaml
automation:
  - alias: "Weekly Update All"
    trigger:
      - platform: time
        at: "02:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: sh_update_manager.scan_all
      - delay: "00:00:30"
      # Start queues individually in priority order
      - service: sh_update_manager.start_queue
        data:
          queue_name: "Z-Wave Firmware"
```

### Example: Notify on Completion

```yaml
automation:
  - alias: "Update Queue Completed Notification"
    trigger:
      - platform: state
        entity_id: sensor.update_queue_z_wave_firmware_last_run_result
        to: "completed"
    action:
      - service: notify.mobile_app
        data:
          title: "Z-Wave Updates Complete"
          message: "All Z-Wave firmware updates finished successfully."
```

### Using HA Schedule Helper

1. Go to **Settings → Helpers → Create Helper → Schedule**.
2. Create a schedule (e.g., "Update Window" — Sunday 2-4 AM).
3. Use the schedule entity in an automation trigger:

```yaml
trigger:
  - platform: state
    entity_id: schedule.update_window
    to: "on"
```

---

## Services Reference

All services are under the `sh_update_manager` domain.

| Service | Description | Required Data |
|---------|-------------|---------------|
| `scan_all` | Scan all queues for pending updates | (none) |
| `scan_queue` | Scan a single queue | `queue_name` |
| `start_queue` | Start processing a queue | `queue_name` |
| `stop_queue` | Stop a running queue | `queue_name` |
| `pause_queue` | Pause a running queue | `queue_name` |
| `resume_queue` | Resume a paused queue | `queue_name` |
| `skip_current` | Skip current item | `queue_name` |
| `clear_queue` | Clear all pending items | `queue_name` |
| `retry_failed` | Retry all failed items | `queue_name` |
| `add_queue` | Create a new queue | `queue_name` + options |
| `edit_queue` | Edit queue settings | `queue_name` + updates |
| `delete_queue` | Delete a queue | `queue_name` |

### add_queue / edit_queue Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `match_type` | string | `integration` | integration, area, label, entity, device_name, manufacturer |
| `match_value` | string | `""` | Comma-separated match values |
| `exclude_pattern` | string | `""` | Comma-separated exclude patterns |
| `exec_mode` | string | `sequential` | sequential or parallel |
| `trigger_mode` | string | `manual` | manual or auto_on_scan |
| `battery_handling` | string | `exclude` | exclude, defer_to_end, include |
| `priority` | int | `50` | 1-100 (lower = higher priority) |
| `stop_on_failure` | bool | `false` | Stop queue on first failure |
| `skip_unavailable` | bool | `true` | Skip unavailable entities |
| `install_delay` | int | `15` | Seconds between installs |
| `install_timeout` | int | `7200` | Max seconds per install |
| `max_retries` | int | `2` | Retry attempts on failure |
| `history_count` | int | `25` | Past runs to keep |

---

## Troubleshooting

### Integration Won't Load

- Check **Settings → System → Logs** and search for `sh_update_manager`.
- Ensure you're on Home Assistant 2024.1+ (required for device-per-queue).
- Try removing and re-adding the integration.

### Sidebar Panel Missing

- The panel registers at `/sh-update-manager`. Try navigating directly to
  `http://your-ha:8123/sh-update-manager`.
- Check logs for "panel registered" or panel-related errors.
- Clear browser cache and reload.

### Scan Finds Fewer Devices Than Expected

- **Battery devices excluded:** Check Battery Handling — set to "include"
  or "defer to end" to see battery devices.
- **Wrong match type:** If using "integration", make sure you have the
  correct platform name (e.g., `zwave_js` not `zwave`).
- **Exclude pattern too broad:** Check your exclude pattern isn't
  accidentally filtering out desired devices.
- **Devices not in "on" state:** Only entities with pending updates
  (`state = on`) are included. Devices already up-to-date won't appear.

### Updates Fail or Time Out

- Increase **Install Timeout** for devices that take longer (some Z-Wave
  firmware updates take 30+ minutes).
- Increase **Install Delay** to give devices more recovery time between
  updates.
- Check device-specific logs for the actual failure reason.
- Use **Retry Failed** to attempt the update again.

### Queue Stuck in "Running"

- Click **Stop** to force-stop the queue.
- If Stop doesn't work, restart Home Assistant.
- Check logs for the stuck entity — it may be an unresponsive device.

### Debug Logging

Add this to your `configuration.yaml` for detailed logs:

```yaml
logger:
  default: warning
  logs:
    custom_components.sh_update_manager: debug
```

Restart HA, then check **Settings → System → Logs** for detailed scan
output showing exactly which entities were matched, excluded, and why.

---

## Version History

| Version | Changes |
|---------|---------|
| v2.0.3 | Rename to Smarter.Homes, advanced filtering (device_name, manufacturer, exclude patterns), sidebar panel Add/Edit/Delete, comprehensive user manual |
| v2.0.2 | Bug fixes, improved scan logging, sidebar panel fixes |
| v2.0.1 | Panel registration fixes, HA version compatibility |
| v2.0.0 | Queue-based architecture, device-per-queue, sidebar panel |
| v1.2.x | Queue selection setup, translation fixes |
| v1.1.0 | Queue management, per-category settings |
| v1.0.0 | Initial release |

---

*by Smarter Homes LLC — [smarter.homes](https://smarter.homes)*
