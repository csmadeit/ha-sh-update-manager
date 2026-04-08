"""Constants for SH Auto Update Manager."""

DOMAIN = "sh_update_manager"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
DEFAULT_INSTALL_DELAY = 15  # seconds between installs
DEFAULT_INSTALL_TIMEOUT = 7200  # 2 hours per device
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAINTENANCE_WINDOW_START = "02:00"
DEFAULT_MAINTENANCE_WINDOW_END = "05:00"

# ---------------------------------------------------------------------------
# Queue states
# ---------------------------------------------------------------------------
QUEUE_STATE_IDLE = "idle"
QUEUE_STATE_RUNNING = "running"
QUEUE_STATE_PAUSED = "paused"
QUEUE_STATE_STOPPED = "stopped"

# ---------------------------------------------------------------------------
# Execution modes — how updates within a group are processed
# ---------------------------------------------------------------------------
EXEC_MODE_SEQUENTIAL = "sequential"  # one at a time, wait for each to finish
EXEC_MODE_PARALLEL = "parallel"  # all at once (safe for independent updates)
EXEC_MODE_DISABLED = "disabled"  # never auto-update, skip entirely
EXEC_MODE_MANUAL_ONLY = "manual_only"  # show in queue but need explicit approval

EXEC_MODES_LIST = [
    EXEC_MODE_SEQUENTIAL,
    EXEC_MODE_PARALLEL,
    EXEC_MODE_DISABLED,
    EXEC_MODE_MANUAL_ONLY,
]

# ---------------------------------------------------------------------------
# Update groups — logical groupings by integration type
# ---------------------------------------------------------------------------
GROUP_ZWAVE = "zwave"
GROUP_ESPHOME = "esphome"
GROUP_HACS = "hacs"
GROUP_HA_CORE = "ha_core"
GROUP_HA_OS = "ha_os"
GROUP_ADDONS = "addons"
GROUP_MATTER = "matter"
GROUP_MQTT = "mqtt"
GROUP_OTHER = "other"

# Map HA integration platforms → group
INTEGRATION_GROUP_MAP: dict[str, str] = {
    "zwave_js": GROUP_ZWAVE,
    "zwave": GROUP_ZWAVE,
    "esphome": GROUP_ESPHOME,
    "hacs": GROUP_HACS,
    "homeassistant": GROUP_HA_CORE,
    "hassio": GROUP_HA_OS,
    "hassio_addons": GROUP_ADDONS,
    "update": GROUP_HA_CORE,
    "matter": GROUP_MATTER,
    "mqtt": GROUP_MQTT,
}

# Default execution mode per group — conservative
DEFAULT_GROUP_MODES: dict[str, str] = {
    GROUP_ZWAVE: EXEC_MODE_SEQUENTIAL,
    GROUP_ESPHOME: EXEC_MODE_SEQUENTIAL,
    GROUP_HACS: EXEC_MODE_DISABLED,
    GROUP_HA_CORE: EXEC_MODE_DISABLED,
    GROUP_HA_OS: EXEC_MODE_DISABLED,
    GROUP_ADDONS: EXEC_MODE_MANUAL_ONLY,
    GROUP_MATTER: EXEC_MODE_SEQUENTIAL,
    GROUP_MQTT: EXEC_MODE_SEQUENTIAL,
    GROUP_OTHER: EXEC_MODE_MANUAL_ONLY,
}

# Human-friendly display names
GROUP_DISPLAY_NAMES: dict[str, str] = {
    GROUP_ZWAVE: "Z-Wave Firmware",
    GROUP_ESPHOME: "ESPHome Devices",
    GROUP_HACS: "HACS Integrations",
    GROUP_HA_CORE: "Home Assistant Core",
    GROUP_HA_OS: "Home Assistant OS",
    GROUP_ADDONS: "Add-ons",
    GROUP_MATTER: "Matter Devices",
    GROUP_MQTT: "MQTT Devices",
    GROUP_OTHER: "Other Updates",
}

# Processing order — device firmware first, system last
GROUP_EXECUTION_ORDER: list[str] = [
    GROUP_ZWAVE,
    GROUP_ESPHOME,
    GROUP_MATTER,
    GROUP_MQTT,
    GROUP_OTHER,
    GROUP_ADDONS,
    GROUP_HACS,
    GROUP_HA_CORE,
    GROUP_HA_OS,
]

# ---------------------------------------------------------------------------
# Queue-item statuses
# ---------------------------------------------------------------------------
ITEM_STATUS_PENDING = "pending"
ITEM_STATUS_APPROVED = "approved"
ITEM_STATUS_INSTALLING = "installing"
ITEM_STATUS_COMPLETED = "completed"
ITEM_STATUS_FAILED = "failed"
ITEM_STATUS_SKIPPED = "skipped"
ITEM_STATUS_WAITING_APPROVAL = "waiting_approval"

# ---------------------------------------------------------------------------
# Config keys — global settings
# ---------------------------------------------------------------------------
CONF_EXCLUDE_ENTITIES = "exclude_entities"
CONF_EXCLUDE_AREAS = "exclude_areas"
CONF_EXCLUDE_LABELS = "exclude_labels"
CONF_AUTO_START = "auto_start"
CONF_INSTALL_DELAY = "install_delay"
CONF_INSTALL_TIMEOUT = "install_timeout"
CONF_MAX_RETRIES = "max_retries"
CONF_MAINTENANCE_WINDOW_ENABLED = "maintenance_window_enabled"
CONF_MAINTENANCE_WINDOW_START = "maintenance_window_start"
CONF_MAINTENANCE_WINDOW_END = "maintenance_window_end"
CONF_STOP_ON_FAILURE = "stop_on_failure"
CONF_SKIP_UNAVAILABLE = "skip_unavailable"

# Per-group config keys (stored as JSON dicts in options)
CONF_GROUP_MODES = "group_modes"
CONF_ZWAVE_MAINS_ONLY = "zwave_mains_only"

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
SERVICE_START_QUEUE = "start_queue"
SERVICE_PAUSE_QUEUE = "pause_queue"
SERVICE_RESUME_QUEUE = "resume_queue"
SERVICE_STOP_QUEUE = "stop_queue"
SERVICE_SKIP_CURRENT = "skip_current"
SERVICE_REFRESH_CANDIDATES = "refresh_candidates"
SERVICE_INSTALL_ALL_ELIGIBLE = "install_all_eligible"
SERVICE_INSTALL_ENTITY = "install_entity"
SERVICE_APPROVE_ITEM = "approve_item"
SERVICE_CLEAR_QUEUE = "clear_queue"

# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------
PLATFORMS = ["sensor", "button", "switch"]

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
STORAGE_KEY = f"{DOMAIN}.queue"
STORAGE_VERSION = 2
