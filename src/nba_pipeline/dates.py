from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def eastern_yesterday(now=None):
    """Return yesterday's date in US Eastern time."""
    now = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/New_York"))
    return (now - timedelta(days=1)).date()