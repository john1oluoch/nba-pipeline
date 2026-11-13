from datetime import date, datetime
from zoneinfo import ZoneInfo
from nba_pipeline.dates import eastern_yesterday

def test_eastern_yesterday():
    # At 02:00 AM on Nov 10, 2026 in Nairobi, it is 18:00 PM on Nov 9 in New York.
    # Therefore, Eastern yesterday should be Nov 8, 2026.
    nairobi_time = datetime(2026, 11, 10, 2, 0, tzinfo=ZoneInfo("Africa/Nairobi"))
    result = eastern_yesterday(now=nairobi_time)
    assert result == date(2026, 11, 8)