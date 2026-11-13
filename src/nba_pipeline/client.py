import logging
import time

from nba_api.stats.endpoints import leaguegamefinder
import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)


class NBAClient:
    """Client for safely fetching game schedules and box scores from stats.nba.com with rate limiting and retries."""

    def __init__(self, sleep_seconds: float = 1.5, timeout: int = 60):
        self.sleep_seconds = sleep_seconds
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(multiplier=2, max=60),
        retry=retry_if_exception_type(
            (
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.HTTPError,
            )
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _call(self, make_endpoint, endpoint_name="unknown"):
        """Private helper that runs an endpoint call with timing, logging, and rate-limiting."""
        start = time.perf_counter()
        try:
            response = make_endpoint()
            elapsed = time.perf_counter() - start
            logger.info("endpoint=%s status=ok seconds=%.2f", endpoint_name, elapsed)
            time.sleep(self.sleep_seconds)
            return response.get_dict()
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.warning("endpoint=%s status=error seconds=%.2f error=%s", endpoint_name, elapsed, exc)
            raise

    def get_games(self, game_date):
        """Fetch all games for a specific date using LeagueGameFinder."""
        d = game_date.strftime("%m/%d/%Y")
        return self._call(
            lambda: leaguegamefinder.LeagueGameFinder(
                date_from_nullable=d,
                date_to_nullable=d,
                league_id_nullable="00",
                timeout=self.timeout,
            ),
            endpoint_name="LeagueGameFinder",
        )

    def get_box_score(self, game_id):
        """Fetch the traditional box score for a specific game ID."""
        from nba_api.stats.endpoints import boxscoretraditionalv3

        return self._call(
            lambda: boxscoretraditionalv3.BoxScoreTraditionalV3(
                game_id=game_id,
                timeout=self.timeout,
            ),
            endpoint_name="BoxScoreTraditionalV3",
        )