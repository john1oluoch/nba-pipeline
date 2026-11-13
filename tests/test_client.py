from datetime import date
from unittest.mock import MagicMock, patch
import requests
from nba_pipeline.client import NBAClient


@patch("nba_pipeline.client.leaguegamefinder.LeagueGameFinder")
def test_client_retry_success(mock_league_finder, monkeypatch):
    # Mock time.sleep so the test runs instantly without pausing
    monkeypatch.setattr("time.sleep", lambda s: None)

    # Set up a mock response object where the first call raises a Timeout,
    # and the second call returns a fake response dictionary.
    fake_response = MagicMock()
    fake_response.get_dict.return_value = {"resultSets": []}

    mock_league_finder.side_effect = [requests.exceptions.Timeout(), fake_response]

    client = NBAClient(sleep_seconds=0.1)
    result = client.get_games(date(2026, 11, 2))

    # Assertions
    assert result == {"resultSets": []}
    assert mock_league_finder.call_count == 2