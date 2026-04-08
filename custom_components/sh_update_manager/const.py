"""Constants for SH Auto Update Manager."""

DOMAIN = "sh_update_manager"

# Default settings
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
DEFAULT_INSTALL_DELAY = 15  # seconds between installs
DEFAULT_INSTALL_TIMEOUT = 7200  # 2 hours per device
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAINTENANCE_WINDOW_START = "02:00"
DEFAULT_MAINTENANCE_WINDOW_END = "05:00"

# Queue states
QUEUE_STATE_IDLE = "idle"
QUEUE_STATE_RUNNING = "running"
QUEUE_STATE_PAUSED = "paused"
QUEUE_STATE_STOPPED = "stopped"

# Update categories
CATEGORY_FIRMWARE = "firmware"
CATEGORY_SOFTWARE = "software"
CATEGORY_ALL = "all"

# Config keys
CONF_INCLUDE_INTEGRATIONS = "include_integrations"
CONF_EXCLUDE_ENTITIES = "exclude_entities"
CONF_EXCLUDE_AREAS = "exclude_areas"
CONF_EXCLUDE_LABELS = "exclude_labels"
CONF_AUTO_UPDATE = "auto_update"
CONF_MAINS_POWERED_ONLY = "mains_powered_only"
CONF_ONE_AT_A_TIME = "one_at_a_time"
CONF_INSTALL_DELAY = "install_delay"
CONF_INSTALL_TIMEOUT = "install_timeout"
CONF_MAX_RETRIES = "max_retries"
CONF_MAINTENANCE_WINDOW_ENABLED = "maintenance_window_enabled"
CONF_MAINTENANCE_WINDOW_START = "maintenance_window_start"
CONF_MAINTENANCE_WINDOW_END = "maintenance_window_end"
CONF_STOP_ON_FAILURE = "stop_on_failure"
CONF_SKIP_UNAVAILABLE = "skip_unavailable"
CONF_CATEGORY_FILTER = "category_filter"

# Services
SERVICE_START_QUEUE = "start_queue"
SERVICE_PAUSE_QUEUE = "pause_queue"
SERVICE_RESUME_QUEUE = "resume_queue"
SERVICE_STOP_QUEUE = "stop_queue"
SERVICE_SKIP_CURRENT = "skip_current"
SERVICE_REFRESH_CANDIDATES = "refresh_candidates"
SERVICE_INSTALL_ALL_ELIGIBLE = "install_all_eligible"
SERVICE_INSTALL_ENTITY = "install_entity"

# Platforms
PLATFORMS = ["sensor", "button", "switch"]

# Storage
STORAGE_KEY = f"{DOMAIN}.queue"
STORAGE_VERSION = 1
