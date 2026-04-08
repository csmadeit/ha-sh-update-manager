# SH Auto Update Manager — Home Assistant Integration

by **Smarter Homes LLC** — [smarter.homes](https://smarter.homes)

A HACS-compatible custom integration that discovers all available Home Assistant updates (Z-Wave firmware, ESPHome, HACS, add-ons, etc.) and installs them **one at a time** with configurable rules, scheduling, and queue management.

**Status:** v1.0.0 — Initial release. Ready for testing.

---

## Session Details

- **Created by:** Chris S (@csmadeit) via Devin AI
- **Repository:** [github.com/csmadeit/ha-sh-update-manager](https://github.com/csmadeit/ha-sh-update-manager)
- **Date:** 2026-04-08

---

## Why This Integration?

Home Assistant exposes firmware and software updates as `update.*` entities. When you have dozens of Z-Wave devices, ESPHome nodes, or HACS integrations with pending updates, you have to manually click "Install" on each one. This integration solves that by:

1. **Discovering** all `update.*` entities with available updates
2. **Filtering** them by your rules (integration, area, labels, device type)
3. **Queuing** them for sequential installation
4. **Installing** them one at a time, waiting for each to finish
5. **Handling** timeouts, retries, and failures gracefully
6. **Respecting** a maintenance window so updates run at safe times

---

## Features

### Queue Management
- Sequential one-at-a-time update installation
- Pause / Resume / Stop / Skip controls
- Persistent queue state across HA restarts
- Configurable delay between installs (default: 15s)
- Configurable timeout per update (default: 2 hours)
- Configurable retry count (default: 2)

### Smart Filtering
- **Include integrations:** Only update entities from specific integrations (e.g., `zwave_js`, `esphome`, `hacs`)
- **Exclude entities:** Skip specific entities by ID
- **Exclude areas:** Skip all entities in certain areas
- **Exclude labels:** Skip entities with certain labels
- **Category filter:** All updates or firmware-only
- **Mains-powered only:** Skip battery devices (important for Z-Wave)
- **Skip unavailable:** Skip sleeping/offline devices

### Scheduling
- **Maintenance window:** Only install updates within a time window (e.g., 2 AM – 5 AM)
- **Auto-update mode:** Automatically start queue when updates are discovered

### Entities Exposed

| Entity | Type | Description |
|--------|------|-------------|
| Queue Status | Sensor | Current state: idle, running, paused, stopped |
| Pending Updates | Sensor | Number of updates waiting to install |
| Current Update Target | Sensor | Entity currently being updated |
| Last Success | Sensor | Last successfully updated entity |
| Last Failure | Sensor | Last failed entity |
| Completed Updates | Sensor | Count of successful updates this session |
| Failed Updates | Sensor | Count of failed updates this session |
| Update All Eligible | Button | Start updating all eligible entities |
| Refresh Update Scan | Button | Rescan for available updates |
| Stop Queue | Button | Stop the queue immediately |
| Skip Current Update | Button | Skip the current update |
| Auto Update Enabled | Switch | Toggle auto-update mode |
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

---

## Files

### Integration Core

| File | Purpose |
|------|---------|
| `__init__.py` | Integration setup, service registration, config entry handling |
| `const.py` | Constants: domain, defaults, config keys, service names |
| `manifest.json` | HACS manifest with metadata |
| `config_flow.py` | Config flow (setup) + Options flow (settings) |
| `queue_manager.py` | Core queue logic: discovery, filtering, sequential install, persistence |
| `services.yaml` | Service definitions for HA Developer Tools |

### Entity Platforms

| File | Purpose |
|------|---------|
| `sensor.py` | 7 sensor entities (queue status, counts, targets) |
| `button.py` | 4 button entities (update all, refresh, stop, skip) |
| `switch.py` | 2 switch entities (auto-update toggle, pause toggle) |

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
3. Configure initial settings (auto-update, mains-only, category filter)
4. Adjust advanced settings in the integration's **Options** (gear icon)

---

## Usage

### Quick Start — Update All Z-Wave Firmware

1. Install and configure the integration
2. In Options, set **Include integrations** to `zwave_js`
3. Enable **Mains-powered only** (recommended for Z-Wave)
4. Press the **Update All Eligible** button (or call `sh_update_manager.install_all_eligible`)
5. Watch the sensors for progress

### Nightly Auto-Update

1. Enable **Auto-update** switch
2. Enable **Maintenance window** in Options
3. Set window to `02:00` – `05:00`
4. The integration will automatically scan and install updates during the window

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
- **Battery Z-Wave devices** may not update reliably unattended — they need to be awake. Use the **mains-powered only** filter for unattended runs.
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
