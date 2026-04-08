# SH Auto Update Manager — Home Assistant Integration

by **Smarter Homes LLC** — [smarter.homes](https://smarter.homes)

A HACS-compatible custom integration that discovers all available Home Assistant updates (Z-Wave firmware, ESPHome, HACS, add-ons, etc.), groups them by integration type, and installs them with **per-group execution modes**, **manual approval workflows**, and **safety overrides** for Z-Wave and HA Core/OS.

**Status:** v1.1.0 — Major upgrade with per-group execution modes and manual queue review.

---

## Session Details

- **Created by:** Chris S (@csmadeit) via Devin AI
- **Repository:** [github.com/csmadeit/ha-sh-update-manager](https://github.com/csmadeit/ha-sh-update-manager)
- **Date:** 2026-04-08

---

## Why This Integration?

Home Assistant exposes firmware and software updates as `update.*` entities. When you have dozens of Z-Wave devices, ESPHome nodes, or HACS integrations with pending updates, you have to manually click "Install" on each one. This integration solves that by:

1. **Discovering** all `update.*` entities with available updates
2. **Grouping** them by integration type (Z-Wave, ESPHome, HACS, HA Core, HA OS, Add-ons, Matter, MQTT, Other)
3. **Applying per-group rules** — sequential, parallel, disabled, or manual-only
4. **Safety overrides** — Z-Wave is ALWAYS sequential; HA Core/OS is ALWAYS sequential
5. **Manual approval** — review the full queue before starting, approve items individually
6. **Installing** them according to group rules with proper tracking
7. **Handling** timeouts, retries, and failures gracefully

---

## What's New in v1.1.0

- **Per-group execution modes** — configure each group independently (sequential, parallel, disabled, manual_only)
- **Update groups** — Z-Wave, ESPHome, HACS, HA Core, HA OS, Add-ons, Matter, MQTT, Other
- **Z-Wave always sequential** — safety override, never parallel, with proper per-device tracking
- **HA Core/OS exclusion** — disabled by default, never auto-updated
- **Manual approval workflow** — items in manual_only groups need explicit approval before installation
- **Full queue visibility** — queue status sensor includes complete item list with groups, versions, and status
- **Waiting Approval sensor** — see how many items need your approval
- **Approve All button** — approve all waiting items with one press
- **Clear Queue button** — reset the queue and counters
- **Multi-step options flow** — Step 1: Global settings, Step 2: Per-group modes, Step 3: Filters
- **Group execution order** — device firmware first (Z-Wave, ESPHome, Matter, MQTT, Other), then add-ons, then HACS, then HA Core/OS last
- **2 new services** — `approve_item` and `clear_queue`

---

## Features

### Per-Group Execution Modes

| Group | Default Mode | Notes |
|-------|-------------|-------|
| Z-Wave Firmware | Sequential | **Always forced sequential** — safety override |
| ESPHome Devices | Sequential | Can be set to parallel |
| HACS Integrations | Disabled | Won't auto-update by default |
| Home Assistant Core | Disabled | Won't auto-update by default |
| Home Assistant OS | Disabled | Won't auto-update by default |
| Add-ons | Manual Only | Needs explicit approval |
| Matter Devices | Sequential | Can be set to parallel |
| MQTT Devices | Sequential | Can be set to parallel |
| Other Updates | Manual Only | Needs explicit approval |

### Execution Modes

- **Sequential** — one at a time, wait for each to finish before starting the next
- **Parallel** — all at once (safe for independent updates like ESPHome)
- **Disabled** — skip entirely, never auto-update
- **Manual Only** — show in queue but require explicit approval before installation

### Queue Management
- Full queue visibility with per-item group, version, and status info
- Manual "Start Queue" button — nothing runs until YOU press it
- Pause / Resume / Stop / Skip controls
- Approve individual items or all waiting items at once
- Clear queue to reset everything
- Persistent queue state across HA restarts
- Configurable delay between installs (default: 15s)
- Configurable timeout per update (default: 2 hours)
- Configurable retry count (default: 2)

### Smart Filtering
- **Exclude entities:** Skip specific entities by ID
- **Exclude areas:** Skip all entities in certain areas
- **Exclude labels:** Skip entities with certain labels
- **Z-Wave mains-powered only:** Skip battery devices (important for Z-Wave)
- **Skip unavailable:** Skip sleeping/offline devices

### Scheduling
- **Maintenance window:** Only install updates within a time window (e.g., 2 AM – 5 AM)
- **Auto-start mode:** Automatically start queue when updates are discovered during refresh

### Entities Exposed

| Entity | Type | Description |
|--------|------|-------------|
| Queue Status | Sensor | Current state + full queue item list in attributes |
| Pending Updates | Sensor | Number of updates ready to install |
| Waiting Approval | Sensor | Number of items needing manual approval |
| Current Update Target | Sensor | Entity currently being updated + details |
| Last Success | Sensor | Last successfully updated entity |
| Last Failure | Sensor | Last failed entity |
| Completed Updates | Sensor | Count of successful updates this session |
| Failed Updates | Sensor | Count of failed updates this session |
| Update All Eligible | Button | Start updating all eligible entities |
| Refresh Update Scan | Button | Rescan for available updates |
| Stop Queue | Button | Stop the queue immediately |
| Skip Current Update | Button | Skip the current update |
| Approve All Waiting | Button | Approve all manual-only items |
| Clear Queue | Button | Clear queue and reset counters |
| Auto Start Queue | Switch | Toggle auto-start mode |
| Pause Queue | Switch | Toggle queue pause |

### Services

| Service | Description |
|---------|-------------|
| `sh_update_manager.start_queue` | Start the update queue |
| `sh_update_manager.pause_queue` | Pause the queue |
| `sh_update_manager.resume_queue` | Resume a paused queue |
| `sh_update_manager.stop_queue` | Stop the queue |
| `sh_update_manager.skip_current` | Skip the current update |
| `sh_update_manager.refresh_candidates` | Rescan for updates |
| `sh_update_manager.install_all_eligible` | Discover and install all |
| `sh_update_manager.install_entity` | Install a specific entity |
| `sh_update_manager.approve_item` | Approve a manual-only item |
| `sh_update_manager.clear_queue` | Clear queue and reset counters |

---

## Files

### Integration Core

| File | Purpose |
|------|---------|
| `__init__.py` | Integration setup, service registration (10 services), config entry handling |
| `const.py` | Constants: execution modes, update groups, group mapping, default modes, execution order |
| `manifest.json` | HACS manifest with metadata |
| `config_flow.py` | Config flow + multi-step Options flow (global → per-group → filters) |
| `queue_manager.py` | Core queue logic: discovery, grouping, per-group execution, safety overrides, persistence |
| `services.yaml` | Service definitions for HA Developer Tools |

### Entity Platforms

| File | Purpose |
|------|---------|
| `sensor.py` | 8 sensor entities (queue status with full list, counts, approval count, targets) |
| `button.py` | 6 button entities (update all, refresh, stop, skip, approve all, clear) |
| `switch.py` | 2 switch entities (auto-start toggle, pause toggle) |

### Translations

| File | Purpose |
|------|---------|
| `strings.json` | Base strings for config/options flows (3 steps) |
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
3. Click **Submit** to create the entry
4. Click the **gear icon** on the integration to open Options
5. **Step 1:** Configure global settings (delays, retries, maintenance window)
6. **Step 2:** Set per-group execution modes (sequential/parallel/disabled/manual_only)
7. **Step 3:** Set exclusion filters (entities, areas, labels)

---

## Usage

### Quick Start — Manual Queue Review

1. Install and configure the integration
2. Set Z-Wave and ESPHome to **sequential** in group modes
3. Set HACS, HA Core, HA OS to **disabled**
4. Press **Refresh Update Scan** to discover available updates
5. Review the Queue Status sensor attributes to see all pending items
6. Press **Update All Eligible** to start the queue
7. Watch the sensors for progress

### With Manual Approval

1. Set desired groups to **manual_only** in group modes
2. Press **Refresh Update Scan** to discover updates
3. Check the **Waiting Approval** sensor to see items needing approval
4. Call `sh_update_manager.approve_item` with the entity_id, or press **Approve All Waiting**
5. Press **Update All Eligible** to start processing approved items

### Nightly Auto-Update

1. Enable **Auto Start Queue** switch
2. Enable **Maintenance window** in Options
3. Set window to `02:00` – `05:00`
4. Create an automation to call `sh_update_manager.refresh_candidates` at 2 AM

### Automation Example

```yaml
automation:
  - alias: "Run update queue nightly"
    triggers:
      - trigger: time
        at: "02:00:00"
    actions:
      - action: sh_update_manager.install_all_eligible
```

---

## Important Notes

- **Z-Wave firmware updates can be risky.** Some manufacturers warn that interrupting a firmware update can brick a device. Use conservative timeouts.
- **Z-Wave is ALWAYS sequential.** Even if you set the mode to parallel, the safety override forces sequential installation.
- **HA Core/OS is ALWAYS sequential.** These updates affect the entire system and must not run alongside other updates.
- **Battery Z-Wave devices** may not update reliably unattended — they need to be awake. The **mains-powered only** filter is enabled by default.
- **The integration uses HA's native `update.install` action.** It does not bypass or modify the standard update mechanism.
- **Queue state persists** across Home Assistant restarts. If HA restarts mid-queue, the queue will resume from where it left off.

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
- 8 sensors, 6 buttons, 2 switches (up from 7/4/2)
- 10 services (up from 8)

### v1.0.0 — 2026-04-08
- Initial release
- Queue manager with sequential update installation
- Config flow + Options flow with full settings
- 7 sensors, 4 buttons, 2 switches
- 8 services for queue control
- Persistent queue state
- Maintenance window support
- Integration/area/label/entity filtering
- Mains-powered-only mode for Z-Wave safety
