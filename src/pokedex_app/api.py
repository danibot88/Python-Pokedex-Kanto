import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__
from .storage import (
    CACHE_DIR,
    SPRITE_DIR,
    atomic_write_bytes,
    atomic_write_text,
    prepare_directories,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://pokeapi.co/api/v2/pokemon"
CACHE_VERSION = 2
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
REQUEST_TIMEOUT = 12


class PokeApiError(RuntimeError):
    pass


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": f"PokedexKanto/{__version__}"})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise PokeApiError(f"A PokéAPI respondeu com erro {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PokeApiError(f"Não foi possível acessar a PokéAPI ({exc}).") from exc


def _read_cache(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Cache inválido descartado (%s): %s", path.name, exc)
        path.unlink(missing_ok=True)
        return None

    if not isinstance(payload, dict) or payload.get("schema") != CACHE_VERSION:
        logger.info("Cache antigo descartado: %s", path.name)
        path.unlink(missing_ok=True)
        return None
    return payload


def _compact_payload(data: object) -> dict:
    if not isinstance(data, dict) or "id" not in data:
        raise PokeApiError("Resposta inesperada da PokéAPI.")

    sprites = data.get("sprites") or {}
    artwork = (sprites.get("other") or {}).get("official-artwork") or {}
    return {
        "schema": CACHE_VERSION,
        "id": data["id"],
        "name": data["name"],
        "height": data["height"] / 10,
        "weight": data["weight"] / 10,
        "types": [item["type"]["name"] for item in data.get("types", [])],
        "abilities": [item["ability"]["name"] for item in data.get("abilities", [])],
        "stats": {item["stat"]["name"]: item["base_stat"] for item in data.get("stats", [])},
        "sprite_url": artwork.get("front_default"),
    }


def pokemon_details(number: int) -> dict:
    prepare_directories()
    cache_file = CACHE_DIR / f"{number}.json"

    cached = _read_cache(cache_file)
    if cached is not None:
        return cached

    raw = _download(f"{BASE_URL}/{number}")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PokeApiError("A PokéAPI retornou uma resposta inválida.") from exc

    compact = _compact_payload(data)
    atomic_write_text(cache_file, json.dumps(compact, ensure_ascii=False))
    return compact


def _is_valid_png(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(len(PNG_SIGNATURE)) == PNG_SIGNATURE
    except OSError:
        return False


def pokemon_sprite(details: dict) -> Path | None:
    prepare_directories()
    target = SPRITE_DIR / f"{details['id']}.png"

    if target.exists() and not _is_valid_png(target):
        logger.warning("Sprite em cache corrompido; baixando novamente: %s", target.name)
        target.unlink(missing_ok=True)
    if target.exists():
        return target

    url = details.get("sprite_url")
    if not url:
        return None

    content = _download(url)
    if not content.startswith(PNG_SIGNATURE):
        raise PokeApiError("A imagem recebida da PokéAPI é inválida.")
    atomic_write_bytes(target, content)
    return target
