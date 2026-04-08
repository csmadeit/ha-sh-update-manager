# SH Auto Update Manager — Home Assistant Integration

by **Smarter Homes LLC** — [smarter.homes](https://smarter.homes)

A HACS-compatible custom integration that creates **named update queues** (e.g., "Z-Wave Firmware", "ESPHome Devices", "HACS Updates") with **independent rules**, **execution modes**, and **per-queue controls** for managing Home Assistant updates.

**Status:** v1.2.2 — Queue-based architecture with queue selection setup.

---

## Session Details

- **Created by:** Chris S (@csmadeit) via Devin AI
- **Repository:** [github.com/csmadeit/ha-sh-update-manager](https://github.com/csmadeit/ha-sh-update-manager)
- **Date:** 2026-04-08

---

## Why This Integration?

Home Assistant exposes firmware and software updates as `update.*` entities. When you have dozens of Z-Wave devices, ESPHome nodes, or HACS integrations with pending updates, you have to manually click "Install" on each one. This integration solves that by:

1. **Creating named queues** — each queue targets a specific set of updates (by integration, area, label, or entity)
2. **Per-queue rules** — sequential or parallel execution, manual or auto trigger
3. **Safety overrides** — Z-Wave is ALWAYS sequential; HA Core/OS excluded by default
4. **Full visibility** — see exactly what's pending in each queue before starting
5. **Independent controls** — start, stop, pause, skip per queue
6. **Auto-created defaults** — 5 queues created automatically based on common integrations

---

## What's New in v1.2.2

- **Queue selection setup** — setup goes straight to queue selection with named checkboxes showing queue name, execution mode, and trigger info
- Each checkbox has a description showing which integrations it matches
- Uncheck all to start empty and build your own custom queues

## What's New in v1.2.0

- **Queue-based architecture** — multiple named queues replace the single global queue
- **Per-queue configuration** — each queue has its own match rule, execution mode, trigger mode, and behavior settings
- **Auto-created default queues** — Z-Wave Firmware, ESPHome Devices, HACS Updates, Add-ons, Other Updates
- **Per-queue entities** — each queue gets its own status sensor, pending count, items list, start/stop/skip buttons, pause switch, enable switch
- **Global controls** — Scan All, Start All, Stop All buttons plus Pause All switch and Overview sensor
- **Queue management UI** — options flow lets you add, edit, remove, enable/disable queues
- **Match rules** — match by integration, area, label, or specific entity IDs
- **Trigger modes** — manual (press button to start) or auto_on_scan (start automatically when updates found)
- **HA Core/OS always excluded** — not included in any default queue (create one manually if you want)
- **Simplified services** — per-queue services with `queue_name` parameter

---

## Features

### Default Queues (Auto-Created)

| Queue Name | Match Rule | Exec Mode | Trigger | Notes |
|------------|-----------|-----------|---------|-------|
| Z-Wave Firmware | zwave_js, zwave | Sequential | Manual | Mains-only enabled |
| ESPHome Devices | esphome | Sequential | Manual | — |
| HACS Updates | hacs | Sequential | Manual | — |
| Add-ons | hassio_addons, hassio | Sequential | Manual | — |
| Other Updates | matter, mqtt | Sequential | Manual | — |

HA Core and HA OS are **not** included in any default queue. You can create a queue for them manually if desired.

### Execution Modes

- **Sequential** — one at a time, wait for each to finish before starting the next
- **Parallel** — all at once (safe for independent updates like ESPHome)

Note: Z-Wave is always forced sequential regardless of setting.

### Trigger Modes

- **Manual** — queue only starts when you press the Start button or call the service
- **Auto on scan** — queue starts automatically when updates are discovered during a scan

### Queue Management
- Add/edit/remove queues in the integration options
- Enable/disable individual queues
- Per-queue start, stop, pause, skip controls
- Global scan all, start all, stop all controls
- Persistent queue state across HA restarts
- Configurable delay between installs (default: 15s)
- Configurable timeout per update (default: 2 hours)
- Configurable retry count (default: 2)

### Match Rules

| Type | Description | Example |
|------|-------------|---------|
| Integration | Match by HA integration platform | `zwave_js,zwave` |
| Area | Match by HA area ID | `living_room,kitchen` |
| Label | Match by HA label | `firmware,critical` |
| Entity | Match specific entity IDs | `update.device_a,update.device_b` |

### Entities Exposed

**Global entities (1 sensor + 3 buttons + 1 switch):**

| Entity | Type | Description |
|--------|------|-------------|
| Update Manager Overview | Sensor | Global state + per-queue summary in attributes |
| Scan All Queues | Button | Scan all enabled queues for new updates |
| Start All Queues | Button | Start all enabled queues with pending updates |
| Stop All Queues | Button | Stop all running queues |
| Pause All Queues | Switch | Pause/resume all running queues |

**Per-queue entities (3 sensors + 3 buttons + 2 switches per queue):**

| Entity | Type | Description |
|--------|------|-------------|
| {Queue} Status | Sensor | Queue state + config details in attributes |
| {Queue} Pending | Sensor | Number of pending updates |
| {Queue} Items | Sensor | Total items count + full item list in attributes |
| Start {Queue} | Button | Start this queue |
| Stop {Queue} | Button | Stop this queue |
| Skip Current in {Queue} | Button | Skip current update |
| Pause {Queue} | Switch | Pause/resume this queue |
| Enable {Queue} | Switch | Enable/disable this queue |

With 5 default queues: **1 overview + 15 sensors + 3 global buttons + 15 queue buttons + 1 global switch + 10 queue switches = 45 entities total**

### Services

| Service | Parameters | Description |
|---------|-----------|-------------|
| `sh_update_manager.scan_all` | — | Scan all enabled queues |
| `sh_update_manager.start_all` | — | Start all enabled queues |
| `sh_update_manager.stop_all` | — | Stop all running queues |
| `sh_update_manager.start_queue` | `queue_name` | Start a specific queue |
| `sh_update_manager.stop_queue` | `queue_name` | Stop a specific queue |
| `sh_update_manager.pause_queue` | `queue_name` | Pause a specific queue |
| `sh_update_manager.resume_queue` | `queue_name` | Resume a paused queue |
| `sh_update_manager.skip_current` | `queue_name` | Skip current update in a queue |
| `sh_update_manager.clear_queue` | `queue_name` | Clear a queue and reset counters |

---

## Files

### Integration Core

| File | Purpose |
|------|---------|
| `__init__.py` | Integration setup, service registration (9 services), config entry handling |
| `const.py` | Constants: queue states, exec/trigger/match modes, default queues, config keys |
| `manifest.json` | HACS manifest with metadata |
| `config_flow.py` | Config flow + Options flow (queue list → add/edit/remove queues) |
| `queue_manager.py` | Core: NamedQueue class, QueueCoordinator, discovery, processing, persistence |
| `services.yaml` | Service definitions for HA Developer Tools |

### Entity Platforms

| File | Purpose |
|------|---------|
| `sensor.py` | Global overview + per-queue status/pending/items sensors |
| `button.py` | Global scan/start/stop + per-queue start/stop/skip buttons |
| `switch.py` | Global pause-all + per-queue pause and enable switches |

### Translations

| File | Purpose |
|------|---------|
| `strings.json` | Base strings for config/options flows |
| `translations/en.json` | English translations |

---

## Module Structure

```
ha-sh-update-manager/
├── README.md
├── SPECIFICATION.md
├── RELEASING.md
├── hacs.json
├── .gitignore
├── docs/
│   ├── DASHBOARD.md
│   └── GITHUB_RELEASE_GOTCHAS.md
├── scripts/
│   └── release.sh
└── custom_components/
    └── sh_update_manager/
        ├── __init__.py
        ├── const.py
        ├── manifest.json
        ├── config_flow.py
        ├── queue_manager.py
        ├── sensor.py
        ├── button.py
        ├── switch.py
        ├── services.yaml
        ├── strings.json
        └── translations/
            └── en.json
```

---

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **Custom Repositories**
3. Add this repository URL: `https://github.com/csmadeit/ha-sh-update-manager`
4. Install **SH Auto Update Manager**
5. Restart Home Assistant

### Manual

1. Copy `custom_components/sh_update_manager/` to your HA `custom_components/` directory
2. Restart Home Assistant

### Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "SH Auto Update Manager"
3. Click **Submit** — default queues are created automatically
4. Click the **gear icon** to manage queues (add, edit, remove, enable/disable)

---

## Usage

### Quick Start

1. Install and configure the integration (default queues are created automatically)
2. Press **Scan All Queues** button to discover available updates
3. Check each queue's **Pending** sensor to see what's waiting
4. Press **Start {Queue Name}** button for the queue you want to run
5. Watch the status sensors for progress

### Example: Update Z-Wave Firmware

1. Press **Scan All Queues** — discovers Z-Wave firmware updates
2. Check **Z-Wave Firmware Pending** sensor — shows how many updates are available
3. Check **Z-Wave Firmware Items** sensor attributes — see the full list of devices
4. Press **Start Z-Wave Firmware** — processes them one at a time sequentially
5. Monitor **Z-Wave Firmware Status** sensor — shows running/idle/completed

### Create a Custom Queue

1. Open integration options (gear icon)
2. Select **Add new queue**
3. Set name (e.g., "Living Room Devices")
4. Set match type to "area" and match value to "living_room"
5. Choose execution mode and trigger mode
6. Save — new entities appear automatically

### Automation Example

```yaml
automation:
  - alias: "Update Z-Wave firmware nightly"
    triggers:
      - trigger: time
        at: "02:00:00"
    actions:
      - action: sh_update_manager.scan_all
      - delay: "00:00:30"
      - action: sh_update_manager.start_queue
        data:
          queue_name: "Z-Wave Firmware"
```

---

## Important Notes

- **Z-Wave firmware updates can be risky.** Some manufacturers warn that interrupting a firmware update can brick a device. Use conservative timeouts.
- **Z-Wave is ALWAYS sequential.** Even if you set the mode to parallel, the safety override forces sequential installation.
- **HA Core/OS is excluded by default.** No default queue targets HA Core or HA OS updates. Create one manually if desired.
- **Battery Z-Wave devices** may not update reliably unattended — they need to be awake. The **mains-powered only** filter is available per queue.
- **The integration uses HA's native `update.install` action.** It does not bypass or modify the standard update mechanism.
- **Queue state persists** across Home Assistant restarts.

---

## Branding

This integration follows the **SH (Smarter Homes)** HACS branding standard:

| Element | Convention |
|---------|-----------|
| Repo prefix | `ha-sh-` |
| Domain prefix | `sh_` |
| HACS display name | `SH {Name}` |
| Full attribution | Smarter Homes LLC — smarter.homes |

---

## Audit Log

### v1.2.2 — 2026-04-08
- Setup goes straight to queue selection with proper names and descriptions
- Each queue checkbox shows: name, execution mode, trigger mode, matched integrations
- Removed unnecessary auto-create toggle

### v1.2.1 — 2026-04-08
- Interactive setup flow with queue selection checkboxes
- Option to start with zero queues and build from scratch

### v1.2.0 — 2026-04-08
- Queue-based architecture — multiple named queues replace single global queue
- Per-queue configuration with match rules, execution modes, trigger modes
- Auto-created default queues (Z-Wave, ESPHome, HACS, Add-ons, Other)
- Per-queue entities (status, pending, items sensors + start/stop/skip buttons + pause/enable switches)
- Global controls (overview sensor, scan/start/stop buttons, pause-all switch)
- Queue management UI in options flow (add/edit/remove queues)
- Match by integration, area, label, or specific entity
- HA Core/OS excluded from all default queues
- 9 services (3 global + 6 per-queue with queue_name parameter)

### v1.1.0 — 2026-04-08
- Per-group execution modes (sequential, parallel, disabled, manual_only)
- 9 update groups with integration-to-group mapping
- Z-Wave always-sequential safety override
- Manual approval workflow for manual_only groups
- Multi-step options flow (global → per-group → filters)
- 8 sensors, 6 buttons, 2 switches, 10 services

### v1.0.0 — 2026-04-08
- Initial release
- Queue manager with sequential update installation
- Config flow + Options flow with full settings
- 7 sensors, 4 buttons, 2 switches, 8 services
- Persistent queue state, maintenance window, filtering
