# Smarter.Homes Update Manager — Dashboard Setup

Since this integration doesn't have its own sidebar page (yet), here's how to
create a dedicated **Update Manager** dashboard view using standard HA cards.

## Quick Setup

1. Go to your HA dashboard → **Edit Dashboard** (pencil icon top right)
2. Click **+ Add Card** → scroll to bottom → **Manual** (YAML)
3. Paste the YAML below
4. Or: create a **new dashboard view** (tab) called "Updates" and add these cards

## Option A: Single Dashboard View (Recommended)

Go to **Settings → Dashboards → + Add Dashboard** → name it "Update Manager".
Then edit it and paste this full view YAML (three-dot menu → Raw configuration editor):

```yaml
views:
  - title: Update Manager
    path: update-manager
    icon: mdi:update
    cards:
      # ── Status Overview ──
      - type: entities
        title: "🔄 Queue Status"
        show_header_toggle: false
        entities:
          - entity: sensor.sh_auto_update_manager_queue_status
            name: Queue Status
          - entity: sensor.sh_auto_update_manager_pending_updates
            name: Pending Updates
          - entity: sensor.sh_auto_update_manager_waiting_approval
            name: Waiting Approval
          - entity: sensor.sh_auto_update_manager_current_update_target
            name: Currently Updating
          - entity: sensor.sh_auto_update_manager_completed_updates
            name: Completed
          - entity: sensor.sh_auto_update_manager_failed_updates
            name: Failed

      # ── Controls ──
      - type: entities
        title: "▶️ Controls"
        show_header_toggle: false
        entities:
          - entity: button.sh_auto_update_manager_refresh_update_scan
            name: "1. Scan for Updates"
            icon: mdi:magnify
          - entity: button.sh_auto_update_manager_update_all_eligible
            name: "2. Start Queue (Update All)"
            icon: mdi:play
          - entity: button.sh_auto_update_manager_approve_all_waiting
            name: "3. Approve All Manual Items"
            icon: mdi:check-all
          - type: divider
          - entity: switch.sh_auto_update_manager_pause_queue
            name: Pause Queue
          - entity: button.sh_auto_update_manager_skip_current_update
            name: Skip Current
          - entity: button.sh_auto_update_manager_stop_queue
            name: Stop Queue
          - entity: button.sh_auto_update_manager_clear_queue
            name: Clear Queue

      # ── Toggles ──
      - type: entities
        title: "⚙️ Settings"
        show_header_toggle: false
        entities:
          - entity: switch.sh_auto_update_manager_auto_start_queue
            name: Auto-Start (start queue on scan)

      # ── History ──
      - type: entities
        title: "📋 History"
        show_header_toggle: false
        entities:
          - entity: sensor.sh_auto_update_manager_last_success
            name: Last Successful Update
          - entity: sensor.sh_auto_update_manager_last_failure
            name: Last Failed Update

      # ── Markdown Queue Details ──
      - type: markdown
        title: "📦 Queue Items"
        content: >-
          {% set items = state_attr('sensor.sh_auto_update_manager_queue_status', 'queue_items') %}
          {% if items and items | length > 0 %}
          | # | Name | Group | Version | Status |
          |---|------|-------|---------|--------|
          {% for item in items %}
          | {{ loop.index }} | {{ item.friendly_name | default(item.entity_id) }} | {{ item.group }} | {{ item.installed_version }} → {{ item.latest_version }} | {{ item.status }} |
          {% endfor %}
          {% else %}
          *No items in queue. Press "Scan for Updates" to discover available updates.*
          {% endif %}
```

## Option B: Add Cards to Existing Dashboard

If you don't want a separate dashboard, add these cards to any existing view:

### Card 1: Status + Controls (compact)

```yaml
type: vertical-stack
cards:
  - type: entities
    title: "Smarter.Homes Update Manager"
    show_header_toggle: false
    entities:
      - entity: sensor.sh_auto_update_manager_queue_status
        name: Status
      - entity: sensor.sh_auto_update_manager_pending_updates
        name: Pending
      - entity: sensor.sh_auto_update_manager_current_update_target
        name: Updating Now
      - type: divider
      - entity: button.sh_auto_update_manager_refresh_update_scan
        name: Scan for Updates
      - entity: button.sh_auto_update_manager_update_all_eligible
        name: Start Queue
      - entity: switch.sh_auto_update_manager_pause_queue
        name: Pause
      - entity: button.sh_auto_update_manager_stop_queue
        name: Stop
```

### Card 2: Queue List (Markdown)

```yaml
type: markdown
title: "Update Queue"
content: >-
  {% set items = state_attr('sensor.sh_auto_update_manager_queue_status', 'queue_items') %}
  {% if items and items | length > 0 %}
  | Name | Group | Version | Status |
  |------|-------|---------|--------|
  {% for item in items %}
  | {{ item.friendly_name | default(item.entity_id) }} | {{ item.group }} | {{ item.installed_version }} → {{ item.latest_version }} | {{ item.status }} |
  {% endfor %}
  {% else %}
  *No items in queue. Press "Scan for Updates" first.*
  {% endif %}
```

## How to Use (Step by Step)

### First Time Setup

1. **Configure per-group rules first:**
   - Settings → Devices & Services → Smarter.Homes Update Manager → **Configure**
   - Step 1: Global settings (leave auto-start OFF if you want manual control)
   - Step 2: Set each group's mode:
     - **Z-Wave:** `sequential` (always one-at-a-time, safe for firmware)
     - **ESPHome:** `sequential` or `parallel`
     - **HA Core:** `disabled` (update manually through the HA Updates page)
     - **HA OS:** `disabled` (update manually)
     - **HACS:** `sequential`
     - **Add-ons:** `sequential`
   - Step 3: Exclude any specific devices/integrations you don't want touched

2. **Add the dashboard** using Option A or B above

### Daily Use

1. **Scan** → Press "Scan for Updates" button
   - The Queue Items table populates with all discovered updates
   - Items are sorted by group: device firmware first, system last
   - Items in `disabled` groups are excluded
   - Items in `manual_only` groups show as "waiting_approval"

2. **Review** → Check the queue table
   - See what will be updated, in what order
   - If items need approval, press "Approve All" or approve individually via service call

3. **Start** → Press "Start Queue"
   - Z-Wave updates run one-by-one with proper tracking
   - ESPHome can run in parallel if you configured it that way
   - HA Core/OS are skipped if disabled
   - Watch "Currently Updating" and "Queue Status" for progress

4. **Monitor** → Watch the sensors update in real-time
   - Pause/resume if needed
   - Skip a stuck update
   - Stop the whole queue if something goes wrong

### Automation Example: Nightly Z-Wave Updates

```yaml
automation:
  - alias: "Nightly Z-Wave firmware queue"
    trigger:
      - platform: time
        at: "02:00:00"
    action:
      - service: sh_update_manager.refresh_candidates
      - delay: "00:00:30"
      - service: sh_update_manager.start_queue
```

## Entity Reference

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.sh_auto_update_manager_queue_status` | Sensor | Queue state (idle/running/paused) + full queue list in attributes |
| `sensor.sh_auto_update_manager_pending_updates` | Sensor | Number of pending updates |
| `sensor.sh_auto_update_manager_waiting_approval` | Sensor | Number of items needing manual approval |
| `sensor.sh_auto_update_manager_current_update_target` | Sensor | Entity currently being updated |
| `sensor.sh_auto_update_manager_last_success` | Sensor | Last successfully updated entity |
| `sensor.sh_auto_update_manager_last_failure` | Sensor | Last failed entity |
| `sensor.sh_auto_update_manager_completed_updates` | Sensor | Count of completed updates |
| `sensor.sh_auto_update_manager_failed_updates` | Sensor | Count of failed updates |
| `button.sh_auto_update_manager_update_all_eligible` | Button | Start updating all eligible entities |
| `button.sh_auto_update_manager_refresh_update_scan` | Button | Discover available updates |
| `button.sh_auto_update_manager_stop_queue` | Button | Stop the queue |
| `button.sh_auto_update_manager_skip_current_update` | Button | Skip the current update |
| `button.sh_auto_update_manager_approve_all_waiting` | Button | Approve all manual-only items |
| `button.sh_auto_update_manager_clear_queue` | Button | Clear the queue and reset counters |
| `switch.sh_auto_update_manager_auto_start_queue` | Switch | Auto-start queue when scan finds updates |
| `switch.sh_auto_update_manager_pause_queue` | Switch | Pause/resume the queue |

## Services

All available under Developer Tools → Services:

| Service | Description |
|---------|-------------|
| `sh_update_manager.start_queue` | Start processing the queue |
| `sh_update_manager.pause_queue` | Pause the queue |
| `sh_update_manager.resume_queue` | Resume a paused queue |
| `sh_update_manager.stop_queue` | Stop the queue entirely |
| `sh_update_manager.skip_current` | Skip the current item |
| `sh_update_manager.refresh_candidates` | Scan for available updates |
| `sh_update_manager.install_all_eligible` | Scan + start queue in one step |
| `sh_update_manager.install_entity` | Install a specific entity by ID |
| `sh_update_manager.approve_item` | Approve a specific manual-only item |
| `sh_update_manager.approve_all` | Approve all waiting items |
