"""Flower configuration for Celery monitoring.

Flower provides a real-time web-based monitoring interface for Celery.
Access the UI at: http://localhost:5555

Features:
- Real-time task monitoring
- Worker status and statistics
- Task history and details
- Queue monitoring
- Rate limiting controls
- Task revocation
- Broker monitoring

Usage:
    # Start Flower
    celery -A config flower --port=5555

    # Start Flower with authentication
    celery -A config flower --port=5555 --basic_auth=user:password

    # Start Flower with persistent state
    celery -A config flower --port=5555 --db=flower.db --persistent=True
"""

from decouple import config

# ============================================================================
# FLOWER CONFIGURATION
# ============================================================================

# Broker URL (same as Celery)
broker_url = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")

# Port for Flower web interface
port = config("FLOWER_PORT", default=5555, cast=int)

# Basic authentication (optional)
# Format: username:password
basic_auth = config("FLOWER_BASIC_AUTH", default="")

# Enable persistent mode to store task history
persistent = config("FLOWER_PERSISTENT", default=True, cast=bool)

# Database for persistent storage
db = config("FLOWER_DB", default="flower.db")

# URL prefix (useful behind reverse proxy)
url_prefix = config("FLOWER_URL_PREFIX", default="")

# Maximum number of tasks to keep in memory
max_tasks = config("FLOWER_MAX_TASKS", default=10000, cast=int)

# Enable debug mode
debug = config("FLOWER_DEBUG", default=False, cast=bool)

# Auto-refresh interval in milliseconds
auto_refresh = config("FLOWER_AUTO_REFRESH", default=True, cast=bool)

# Enable/disable specific features
enable_events = True
inspect = True
inspect_timeout = 10000  # milliseconds

# Timezone
timezone = config("TIME_ZONE", default="UTC")

# ============================================================================
# AUTHENTICATION & SECURITY
# ============================================================================

# OAuth2 authentication (optional)
# oauth2_key = config('FLOWER_OAUTH2_KEY', default='')
# oauth2_secret = config('FLOWER_OAUTH2_SECRET', default='')
# oauth2_redirect_uri = config('FLOWER_OAUTH2_REDIRECT_URI', default='')

# SSL/TLS configuration (optional)
# certfile = config('FLOWER_CERTFILE', default='')
# keyfile = config('FLOWER_KEYFILE', default='')

# ============================================================================
# TASK FILTERING
# ============================================================================

# Hide tasks by name pattern
# task_name_blacklist = ['celery.*']

# Show only these tasks
# task_name_whitelist = ['future_skills.*']

# ============================================================================
# CUSTOMIZATION
# ============================================================================

# Custom page title
page_title = "SmartHR360 Celery Monitor"

# Natural time display
natural_time = True

# ============================================================================
# LOGGING
# ============================================================================

logging = "INFO"

# Log format
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# RATE LIMITING
# ============================================================================

# Rate limit for task execution (tasks per second)
# max_tasks_per_child = 100

# Rate limit for specific tasks
# task_routes = {
#     'future_skills.train_model': {'rate_limit': '10/m'},  # 10 per minute
#     'future_skills.cleanup_old_models': {'rate_limit': '1/h'},  # 1 per hour
# }
