from nba_pipeline.ingest import raw_path


def test_raw_path(tmp_path):
    path = raw_path(str(tmp_path), "games", "2026-11-02", "games")
    expected = tmp_path / "games" / "game_date=2026-11-02" / "games.json"
    assert path == expected