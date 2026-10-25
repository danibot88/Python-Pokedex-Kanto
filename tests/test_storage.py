import json
import logging
import os

import pytest
from src.pokedex_app import storage


@pytest.fixture
def app_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "APP_DIR", tmp_path)
    monkeypatch.setattr(storage, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(storage, "SPRITE_DIR", tmp_path / "sprites")
    monkeypatch.setattr(storage, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(storage, "FAVORITES_FILE", tmp_path / "favorites.json")
    return tmp_path


def test_prepare_directories_creates_all_folders(app_dir):
    storage.prepare_directories()

    assert storage.CACHE_DIR.is_dir()
    assert storage.SPRITE_DIR.is_dir()
    assert storage.LOG_DIR.is_dir()


def test_favorites_roundtrip(app_dir):
    storage.save_favorites({25, 1, 4})

    assert storage.FAVORITES_FILE.read_text(encoding="utf-8") == "[1, 4, 25]"
    assert storage.load_favorites() == {1, 4, 25}


def test_load_favorites_without_file_returns_empty_set(app_dir):
    assert storage.load_favorites() == set()


def test_load_favorites_with_corrupted_json_returns_empty_set(app_dir):
    storage.FAVORITES_FILE.write_text("{isso não é json", encoding="utf-8")

    assert storage.load_favorites() == set()


def test_load_favorites_ignores_non_list_content(app_dir):
    storage.FAVORITES_FILE.write_text(json.dumps({"1": True}), encoding="utf-8")

    assert storage.load_favorites() == set()


def test_load_favorites_filters_invalid_entries(app_dir):
    storage.FAVORITES_FILE.write_text(
        json.dumps([1, "2", "x", True, -5, None, 3.7, 25]), encoding="utf-8"
    )

    assert storage.load_favorites() == {1, 2, 3, 25}


def test_atomic_write_replaces_content_without_leftovers(app_dir):
    target = app_dir / "cache" / "1.json"

    storage.atomic_write_text(target, "primeiro")
    storage.atomic_write_text(target, "segundo")

    assert target.read_text(encoding="utf-8") == "segundo"
    assert list(target.parent.iterdir()) == [target]


def test_save_favorites_does_not_raise_on_disk_error(app_dir, monkeypatch, caplog):
    def failing_write(path, content):
        raise OSError("disco cheio")

    monkeypatch.setattr(storage, "atomic_write_text", failing_write)

    with caplog.at_level(logging.ERROR):
        storage.save_favorites({1})

    assert "favoritos" in caplog.text


def test_app_dir_can_be_overridden_by_environment(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    custom_dir = tmp_path / "personalizado"
    env = {**os.environ, "POKEDEX_APP_DIR": str(custom_dir)}

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from src.pokedex_app.storage import APP_DIR, FAVORITES_FILE;"
            " print(APP_DIR); print(FAVORITES_FILE)",
        ],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    lines = result.stdout.strip().splitlines()
    assert lines == [str(custom_dir), str(custom_dir / "favorites.json")]
