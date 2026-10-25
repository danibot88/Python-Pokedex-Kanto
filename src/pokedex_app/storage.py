import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_APP_DIR = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "PokedexKanto"
APP_DIR = Path(os.getenv("POKEDEX_APP_DIR") or _DEFAULT_APP_DIR)
CACHE_DIR = APP_DIR / "cache"
SPRITE_DIR = APP_DIR / "sprites"
LOG_DIR = APP_DIR / "logs"
FAVORITES_FILE = APP_DIR / "favorites.json"


def prepare_directories() -> None:
    for directory in (CACHE_DIR, SPRITE_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Escreve ``content`` em ``path`` de forma atômica (temporário + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle_fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle_fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, content: str) -> None:
    atomic_write_bytes(path, content.encode("utf-8"))


def load_favorites() -> set[int]:
    try:
        raw = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set()
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Não foi possível ler os favoritos: %s", exc)
        return set()

    if not isinstance(raw, list):
        logger.warning("Arquivo de favoritos inválido; ignorando o conteúdo.")
        return set()

    favorites: set[int] = set()
    for item in raw:
        if isinstance(item, bool):
            continue
        try:
            number = int(item)
        except (TypeError, ValueError):
            logger.debug("Entrada de favorito ignorada: %r", item)
            continue
        if number > 0:
            favorites.add(number)
    return favorites


def save_favorites(favorites: set[int]) -> None:
    try:
        prepare_directories()
        atomic_write_text(FAVORITES_FILE, json.dumps(sorted(favorites)))
    except OSError as exc:
        logger.error("Não foi possível salvar os favoritos: %s", exc)
