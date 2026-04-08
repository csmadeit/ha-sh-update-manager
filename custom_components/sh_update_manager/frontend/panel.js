/**
 * SH Auto Update Manager — Sidebar Panel v2.0.0
 * LitElement-based queue management UI.
 *
 * by Smarter Homes LLC — smarter.homes
 */

import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@3.3.3/lit-element.js?module";

class SHUpdateManagerPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      panel: { type: Object },
      _queues: { type: Array },
      _loading: { type: Boolean },
      _selectedQueue: { type: Number },
      _showHistory: { type: Boolean },
    };
  }

  static get styles() {
    return css`
      :host {
        display: block;
        padding: 16px;
        font-family: var(--primary-font-family, Roboto, sans-serif);
        color: var(--primary-text-color);
        background: var(--primary-background-color);
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
        flex-wrap: wrap;
        gap: 8px;
      }
      .header h1 {
        margin: 0;
        font-size: 24px;
        font-weight: 500;
      }
      .header-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      .btn {
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: background 0.2s;
      }
      .btn-primary {
        background: var(--primary-color, #03a9f4);
        color: white;
      }
      .btn-primary:hover { opacity: 0.9; }
      .btn-danger {
        background: var(--error-color, #db4437);
        color: white;
      }
      .btn-danger:hover { opacity: 0.9; }
      .btn-secondary {
        background: var(--secondary-background-color, #e0e0e0);
        color: var(--primary-text-color);
      }
      .btn-success {
        background: var(--success-color, #4caf50);
        color: white;
      }
      .queue-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        gap: 16px;
      }
      .queue-card {
        background: var(--card-background-color, white);
        border-radius: 8px;
        padding: 16px;
        box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.1));
        border-left: 4px solid var(--primary-color, #03a9f4);
      }
      .queue-card.running {
        border-left-color: var(--success-color, #4caf50);
      }
      .queue-card.paused {
        border-left-color: var(--warning-color, #ff9800);
      }
      .queue-card.stopped {
        border-left-color: var(--error-color, #db4437);
      }
      .queue-name {
        font-size: 18px;
        font-weight: 500;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .queue-status {
        font-size: 12px;
        padding: 2px 8px;
        border-radius: 12px;
        text-transform: uppercase;
        font-weight: 600;
      }
      .status-idle { background: #e0e0e0; color: #616161; }
      .status-running { background: #c8e6c9; color: #2e7d32; }
      .status-paused { background: #fff3e0; color: #e65100; }
      .status-stopped { background: #ffcdd2; color: #c62828; }
      .queue-meta {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 4px 16px;
        font-size: 13px;
        color: var(--secondary-text-color);
        margin-bottom: 12px;
      }
      .queue-meta dt { font-weight: 500; }
      .queue-meta dd { margin: 0; }
      .queue-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 8px;
      }
      .queue-actions .btn { padding: 6px 12px; font-size: 13px; }
      .items-list {
        margin-top: 8px;
        max-height: 200px;
        overflow-y: auto;
        font-size: 13px;
      }
      .item-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }
      .item-status-pending { color: var(--primary-color, #03a9f4); }
      .item-status-installing { color: var(--warning-color, #ff9800); }
      .item-status-completed { color: var(--success-color, #4caf50); }
      .item-status-failed { color: var(--error-color, #db4437); }
      .item-status-skipped { color: var(--secondary-text-color, #757575); }
      .history-section {
        margin-top: 16px;
        padding: 16px;
        background: var(--card-background-color, white);
        border-radius: 8px;
        box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.1));
      }
      .history-run {
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        font-size: 13px;
      }
      .badge {
        display: inline-block;
        padding: 1px 6px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 600;
      }
      .badge-battery { background: #fff9c4; color: #f57f17; }
      .empty-state {
        text-align: center;
        padding: 48px;
        color: var(--secondary-text-color);
      }
      .loading { text-align: center; padding: 48px; }
    `;
  }

  constructor() {
    super();
    this._queues = [];
    this._loading = true;
    this._selectedQueue = -1;
    this._showHistory = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadData();
    this._interval = setInterval(() => this._loadData(), 5000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._interval) clearInterval(this._interval);
  }

  async _loadData() {
    if (!this.hass) return;
    try {
      const states = this.hass.states;
      const queues = [];
      const queueEntities = {};

      // Find all queue devices by looking for status sensors
      for (const [entityId, state] of Object.entries(states)) {
        if (!entityId.startsWith("sensor.") || !entityId.includes("update_queue_")) continue;

        // Extract queue slug from entity_id
        const match = entityId.match(/sensor\.update_queue_(.+?)_(status|pending_updates|queue_items|last_run_result|update_history)$/);
        if (!match) continue;

        const slug = match[1];
        const type = match[2];
        if (!queueEntities[slug]) queueEntities[slug] = {};
        queueEntities[slug][type] = state;
      }

      for (const [slug, entities] of Object.entries(queueEntities)) {
        const status = entities.status;
        if (!status) continue;
        const attrs = status.attributes || {};
        const itemsSensor = entities.queue_items;
        const items = itemsSensor?.attributes?.items || [];
        const pendingSensor = entities.pending_updates;
        const lastRunSensor = entities.last_run_result;
        const historySensor = entities.update_history;

        queues.push({
          slug,
          name: (status.attributes?.friendly_name || slug).replace("Update Queue: ", "").replace(" Status", ""),
          state: status.state,
          exec_mode: attrs.exec_mode || "sequential",
          trigger_mode: attrs.trigger_mode || "manual",
          battery_handling: attrs.battery_handling || "exclude",
          priority: attrs.priority || 50,
          match_type: attrs.match_type || "",
          match_value: attrs.match_value || "",
          pending: pendingSensor ? parseInt(pendingSensor.state) || 0 : 0,
          pending_summary: pendingSensor?.attributes?.summary || "",
          completed: pendingSensor?.attributes?.completed || 0,
          failed: pendingSensor?.attributes?.failed || 0,
          items: items,
          last_run: lastRunSensor?.attributes || null,
          last_run_result: lastRunSensor?.state || "idle",
          history_count: historySensor ? parseInt(historySensor.state) || 0 : 0,
          history: historySensor?.attributes?.runs || [],
        });
      }

      queues.sort((a, b) => a.priority - b.priority);
      this._queues = queues;
      this._loading = false;
    } catch (e) {
      console.error("SH Update Manager: error loading data", e);
      this._loading = false;
    }
  }

  async _callService(service, data = {}) {
    try {
      await this.hass.callService("sh_update_manager", service, data);
      setTimeout(() => this._loadData(), 1000);
    } catch (e) {
      console.error("Service call failed:", e);
    }
  }

  _scanAll() { this._callService("scan_all"); }
  _stopAll() { this._callService("stop_all"); }
  _scanQueue(name) { this._callService("scan_queue", { queue_name: name }); }
  _startQueue(name) { this._callService("start_queue", { queue_name: name }); }
  _stopQueue(name) { this._callService("stop_queue", { queue_name: name }); }
  _pauseQueue(name) { this._callService("pause_queue", { queue_name: name }); }
  _resumeQueue(name) { this._callService("resume_queue", { queue_name: name }); }
  _skipCurrent(name) { this._callService("skip_current", { queue_name: name }); }
  _retryFailed(name) { this._callService("retry_failed", { queue_name: name }); }

  _toggleHistory(idx) {
    this._selectedQueue = this._selectedQueue === idx ? -1 : idx;
    this._showHistory = this._selectedQueue >= 0;
    this.requestUpdate();
  }

  _renderItem(item) {
    return html`
      <div class="item-row">
        <span>
          ${item.friendly_name || item.entity_id}
          ${item.is_battery ? html`<span class="badge badge-battery">Battery</span>` : ""}
        </span>
        <span>
          <span class="item-status-${item.status}">${item.status}</span>
          ${item.installed_version && item.latest_version
            ? html` <small>${item.installed_version} &rarr; ${item.latest_version}</small>`
            : ""}
          ${item.error ? html`<br><small style="color:var(--error-color)">${item.error}</small>` : ""}
        </span>
      </div>
    `;
  }

  _renderQueue(queue, idx) {
    return html`
      <div class="queue-card ${queue.state}">
        <div class="queue-name">
          <span>${queue.name}</span>
          <span class="queue-status status-${queue.state}">${queue.state}</span>
        </div>
        <dl class="queue-meta">
          <dt>Priority</dt><dd>${queue.priority}</dd>
          <dt>Mode</dt><dd>${queue.exec_mode}</dd>
          <dt>Trigger</dt><dd>${queue.trigger_mode}</dd>
          <dt>Battery</dt><dd>${queue.battery_handling}</dd>
          <dt>Pending</dt><dd>${queue.pending_summary || queue.pending}</dd>
          <dt>Last Run</dt><dd>${queue.last_run_result}</dd>
        </dl>

        <div class="queue-actions">
          <button class="btn btn-primary" @click=${() => this._scanQueue(queue.name)}>Scan</button>
          ${queue.state === "idle" || queue.state === "stopped"
            ? html`<button class="btn btn-success" @click=${() => this._startQueue(queue.name)}>Start</button>`
            : ""}
          ${queue.state === "running"
            ? html`
              <button class="btn btn-secondary" @click=${() => this._pauseQueue(queue.name)}>Pause</button>
              <button class="btn btn-danger" @click=${() => this._stopQueue(queue.name)}>Stop</button>
              <button class="btn btn-secondary" @click=${() => this._skipCurrent(queue.name)}>Skip</button>
            ` : ""}
          ${queue.state === "paused"
            ? html`<button class="btn btn-success" @click=${() => this._resumeQueue(queue.name)}>Resume</button>`
            : ""}
          ${queue.failed > 0
            ? html`<button class="btn btn-danger" @click=${() => this._retryFailed(queue.name)}>Retry Failed (${queue.failed})</button>`
            : ""}
          <button class="btn btn-secondary" @click=${() => this._toggleHistory(idx)}>
            History (${queue.history_count})
          </button>
        </div>

        ${queue.items.length > 0 ? html`
          <div class="items-list">
            ${queue.items.map(item => this._renderItem(item))}
          </div>
        ` : ""}
      </div>
    `;
  }

  _renderHistory() {
    if (this._selectedQueue < 0 || this._selectedQueue >= this._queues.length) return "";
    const queue = this._queues[this._selectedQueue];
    if (!queue.history || queue.history.length === 0) {
      return html`<div class="history-section"><p>No run history yet.</p></div>`;
    }
    return html`
      <div class="history-section">
        <h3>Run History: ${queue.name}</h3>
        ${queue.history.map(run => html`
          <div class="history-run">
            <strong>Run #${run.run_id}</strong> — ${run.result}
            ${run.duration ? html` (${run.duration})` : ""}
            <br>
            <small>
              ${run.succeeded} succeeded, ${run.failed} failed, ${run.skipped} skipped
              ${run.started ? html` | Started: ${new Date(run.started).toLocaleString()}` : ""}
            </small>
            ${run.failed_items?.length > 0 ? html`
              <div style="margin-top:4px;color:var(--error-color)">
                Failed: ${run.failed_items.map(f => f.friendly_name || f.entity_id).join(", ")}
              </div>
            ` : ""}
          </div>
        `)}
      </div>
    `;
  }

  render() {
    if (this._loading) {
      return html`<div class="loading">Loading queues...</div>`;
    }

    return html`
      <div class="header">
        <h1>SH Update Manager</h1>
        <div class="header-actions">
          <button class="btn btn-primary" @click=${this._scanAll}>Scan All Queues</button>
          <button class="btn btn-danger" @click=${this._stopAll}>Stop All</button>
          <button class="btn btn-secondary" @click=${() => this._loadData()}>Refresh</button>
        </div>
      </div>

      ${this._queues.length === 0
        ? html`
          <div class="empty-state">
            <p>No queues configured yet.</p>
            <p>Go to Settings &rarr; Devices &amp; Services &rarr; SH Auto Update Manager &rarr; Configure to add queues.</p>
          </div>
        `
        : html`
          <div class="queue-grid">
            ${this._queues.map((q, i) => this._renderQueue(q, i))}
          </div>
          ${this._showHistory ? this._renderHistory() : ""}
        `
      }
    `;
  }
}

customElements.define("sh-update-manager-panel", SHUpdateManagerPanel);
