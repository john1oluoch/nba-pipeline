import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from nba_pipeline.client import NBAClient
from nba_pipeline.dates import eastern_yesterday

logger = logging.getLogger(__name__)


def raw_path(base: str, endpoint: str, game_date: str, name: str) -> Path:
    """Builds a Hive-style partitioned path for raw JSON storage."""
    return Path(base) / endpoint / f"game_date={game_date}" / f"{name}.json"


def write_json(path: Path, payload: dict) -> None:
    """Safely writes JSON data using an atomic replacement to prevent half-written files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(temp_path, path)


def main():
    start_time = time.perf_counter()

    parser = argparse.ArgumentParser(description="Ingest daily NBA games and box scores.")
    parser.add_argument(
        "--date",
        default=eastern_yesterday().isoformat(),
        help="Game date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--out-dir",
        default="data/raw",
        help="Base directory for raw storage files",
    )
    args = parser.parse_args()

    game_date_str = args.date
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    logger.info("Starting ingestion configuration for game_date=%s, out_dir=%s", game_date_str, args.out_dir)

    try:
        dt_obj = datetime.strptime(game_date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        logger.error("Invalid date format. Expected YYYY-MM-DD, got %s", game_date_str)
        raise exc

    client = NBAClient()

    # 1. Fetch games for the target date
    try:
        games_payload = client.get_games(dt_obj)
    except Exception as exc:
        logger.error("Failed to fetch games for %s: %s", game_date_str, exc)
        raise

    # 2. Save games response wrapped in an envelope
    games_file_path = raw_path(args.out_dir, "games", game_date_str, "games")
    games_envelope = {
        "meta": {
            "source": "nba_api",
            "endpoint": "LeagueGameFinder",
            "game_date": game_date_str,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        },
        "data": games_payload,
    }
    write_json(games_file_path, games_envelope)
    logger.info("Saved games list to %s", games_file_path)

    # 3. Extract game IDs from the response structure
    try:
        result_sets = games_payload.get("resultSets", [])
        if not result_sets:
            logger.info("No game result sets found for %s", game_date_str)
            total_elapsed = time.perf_counter() - start_time
            logger.info("Ingestion complete. games_found=0 box_scores_saved=0 total_seconds=%.2f", total_elapsed)
            return

        headers = result_sets[0].get("headers", [])
        row_set = result_sets[0].get("rowSet", [])

        if "GAME_ID" not in headers:
            logger.warning("GAME_ID header not found in result sets for %s", game_date_str)
            total_elapsed = time.perf_counter() - start_time
            logger.info("Ingestion complete. games_found=0 box_scores_saved=0 total_seconds=%.2f", total_elapsed)
            return

        game_id_idx = headers.index("GAME_ID")
        game_ids = {row[game_id_idx] for row in row_set}
    except (ValueError, IndexError) as exc:
        logger.error("Could not parse game IDs from games payload: %s", exc)
        raise

    logger.info("Found %d unique games for %s", len(game_ids), game_date_str)

    # 4. Loop over game IDs and fetch traditional box scores
    box_scores_saved = 0
    for g_id in game_ids:
        try:
            box_score_payload = client.get_box_score(g_id)
            box_path = raw_path(args.out_dir, "box_scores", game_date_str, g_id)
            box_envelope = {
                "meta": {
                    "source": "nba_api",
                    "endpoint": "BoxScoreTraditionalV3",
                    "game_date": game_date_str,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                },
                "data": box_score_payload,
            }
            write_json(box_path, box_envelope)
            box_scores_saved += 1
        except Exception as exc:
            logger.error("Failed to fetch/save box score for game_id=%s: %s", g_id, exc)

    total_elapsed = time.perf_counter() - start_time
    logger.info(
        "Ingestion complete. games_found=%d box_scores_saved=%d total_seconds=%.2f",
        len(game_ids),
        box_scores_saved,
        total_elapsed,
    )


if __name__ == "__main__":
    main()
