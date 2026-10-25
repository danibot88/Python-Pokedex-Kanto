import json
import os
from pathlib import Path


APP_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / "PokedexKanto"
CACHE_DIR = APP_DIR / "cache"
SPRITE_DIR = APP_DIR / "sprites"
FAVORITES_FILE = APP_DIR / "favorites.json"


def prepare_directories() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    SPRITE_DIR.mkdir(parents=True, exist_ok=True)


def load_favorites() -> set[int]:
    try:
        return set(json.loads(FAVORITES_FILE.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return set()


def save_favorites(favorites: set[int]) -> None:
    prepare_directories()
    FAVORITES_FILE.write_text(
        json.dumps(sorted(favorites), ensure_ascii=False), encoding="utf-8"
    )

