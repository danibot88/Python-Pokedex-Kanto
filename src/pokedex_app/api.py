import json
import urllib.error
import urllib.request
from pathlib import Path

from .storage import CACHE_DIR, SPRITE_DIR, prepare_directories


BASE_URL = "https://pokeapi.co/api/v2/pokemon"


class PokeApiError(RuntimeError):
    pass


def _download(url: str, target: Path | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "PokedexKanto/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            content = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PokeApiError("Não foi possível acessar a PokéAPI.") from exc
    if target:
        target.write_bytes(content)
    return content


def pokemon_details(number: int) -> dict:
    prepare_directories()
    cache_file = CACHE_DIR / f"{number}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache_file.unlink(missing_ok=True)

    raw = _download(f"{BASE_URL}/{number}")
    data = json.loads(raw.decode("utf-8"))
    compact = {
        "id": data["id"],
        "name": data["name"],
        "height": data["height"] / 10,
        "weight": data["weight"] / 10,
        "types": [item["type"]["name"] for item in data["types"]],
        "abilities": [item["ability"]["name"] for item in data["abilities"]],
        "stats": {item["stat"]["name"]: item["base_stat"] for item in data["stats"]},
        "sprite_url": data["sprites"]["other"]["official-artwork"]["front_default"],
    }
    cache_file.write_text(json.dumps(compact, ensure_ascii=False), encoding="utf-8")
    return compact


def pokemon_sprite(details: dict) -> Path | None:
    prepare_directories()
    target = SPRITE_DIR / f"{details['id']}.png"
    if target.exists():
        return target
    url = details.get("sprite_url")
    if not url:
        return None
    _download(url, target)
    return target



