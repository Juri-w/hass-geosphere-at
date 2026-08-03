"""Constants for Geosphere Austria integration."""

from datetime import timedelta

DOMAIN = "geosphere_at"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)

API_BASE_URL = "https://www.geosphere.at/data/forecasts"
API_POINTS = f"{API_BASE_URL}/points"
API_FLEXI = f"{API_BASE_URL}/flexi"
API_DAILY = f"{API_BASE_URL}/daily"

API_NOWCAST_BASE = "https://dataset.api.hub.geosphere.at/v1/timeseries/forecast"
API_NOWCAST = f"{API_NOWCAST_BASE}/nowcast-v1-15min-1km"

MODE_REGIONAL = "regional"
MODE_LOCAL_NEW = "local_new"
MODE_LOCAL_UPDATE = "local_update"