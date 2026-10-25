import json
import urllib.error

import pytest
from src.pokedex_app import api


def _payload(number: int = 1) -> dict:
    return {
        "id": number,
        "name": "bulbasaur",
        "height": 7,
        "weight": 69,
        "types": [{"type": {"name": "grass"}}, {"type": {"name": "poison"}}],
        "abilities": [
            {"ability": {"name": "overgrow"}},
            {"ability": {"name": "chlorophyll"}},
        ],
        "stats": [
            {"base_stat": 45, "stat": {"name": "hp"}},
            {"base_stat": 49, "stat": {"name": "attack"}},
        ],
        "sprites": {"other": {"official-artwork": {"front_default": "https://img.test/1.png"}}},
    }


@pytest.fixture
def api_dirs(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    sprite_dir = tmp_path / "sprites"
    monkeypatch.setattr(api, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(api, "SPRITE_DIR", sprite_dir)
    return cache_dir, sprite_dir


def test_pokemon_details_parses_and_caches(api_dirs, monkeypatch):
    cache_dir, _ = api_dirs
    calls = []

    def fake_download(url):
        calls.append(url)
        return json.dumps(_payload()).encode("utf-8")

    monkeypatch.setattr(api, "_download", fake_download)

    details = api.pokemon_details(1)

    assert details["schema"] == api.CACHE_VERSION
    assert details["id"] == 1
    assert details["height"] == pytest.approx(0.7)
    assert details["weight"] == pytest.approx(6.9)
    assert details["types"] == ["grass", "poison"]
    assert details["abilities"] == ["overgrow", "chlorophyll"]
    assert details["stats"] == {"hp": 45, "attack": 49}
    assert details["sprite_url"] == "https://img.test/1.png"
    assert len(calls) == 1
    assert json.loads((cache_dir / "1.json").read_text(encoding="utf-8")) == details


def test_pokemon_details_uses_cache_without_downloading_again(api_dirs, monkeypatch):
    cache_dir, _ = api_dirs
    calls = []

    def fake_download(url):
        calls.append(url)
        return json.dumps(_payload()).encode("utf-8")

    monkeypatch.setattr(api, "_download", fake_download)

    first = api.pokemon_details(1)
    second = api.pokemon_details(1)

    assert first == second
    assert len(calls) == 1
    assert (cache_dir / "1.json").exists()


def test_pokemon_details_redownloads_after_corrupted_cache(api_dirs, monkeypatch):
    cache_dir, _ = api_dirs
    cache_dir.mkdir(parents=True)
    (cache_dir / "1.json").write_text("{invalido", encoding="utf-8")
    calls = []

    def fake_download(url):
        calls.append(url)
        return json.dumps(_payload()).encode("utf-8")

    monkeypatch.setattr(api, "_download", fake_download)

    details = api.pokemon_details(1)

    assert details["id"] == 1
    assert len(calls) == 1
    assert json.loads((cache_dir / "1.json").read_text(encoding="utf-8"))["id"] == 1


def test_pokemon_details_discards_cache_from_older_schema(api_dirs, monkeypatch):
    cache_dir, _ = api_dirs
    cache_dir.mkdir(parents=True)
    (cache_dir / "1.json").write_text(
        json.dumps({"schema": 1, "id": 999, "name": "antigo"}), encoding="utf-8"
    )
    calls = []

    def fake_download(url):
        calls.append(url)
        return json.dumps(_payload()).encode("utf-8")

    monkeypatch.setattr(api, "_download", fake_download)

    details = api.pokemon_details(1)

    assert details["id"] == 1
    assert len(calls) == 1


def test_pokemon_details_rejects_invalid_json_body(api_dirs, monkeypatch):
    monkeypatch.setattr(api, "_download", lambda url: b"<html>portal cativo</html>")

    with pytest.raises(api.PokeApiError, match="inválida"):
        api.pokemon_details(1)


def test_pokemon_details_rejects_unexpected_payload(api_dirs, monkeypatch):
    monkeypatch.setattr(api, "_download", lambda url: b"[]")

    with pytest.raises(api.PokeApiError, match="inesperada"):
        api.pokemon_details(1)


def test_download_wraps_network_errors(monkeypatch):
    def failing_urlopen(*args, **kwargs):
        raise urllib.error.URLError("sem rede")

    monkeypatch.setattr(api.urllib.request, "urlopen", failing_urlopen)

    with pytest.raises(api.PokeApiError, match="PokéAPI"):
        api._download("https://pokeapi.co/api/v2/pokemon/1")


def test_download_reports_http_errors(monkeypatch):
    def failing_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError("https://x", 503, "indisponível", None, None)

    monkeypatch.setattr(api.urllib.request, "urlopen", failing_urlopen)

    with pytest.raises(api.PokeApiError, match="503"):
        api._download("https://pokeapi.co/api/v2/pokemon/1")


def test_sprite_is_downloaded_once(api_dirs, monkeypatch):
    _, sprite_dir = api_dirs
    png = api.PNG_SIGNATURE + b"conteudo"
    calls = []

    def fake_download(url):
        calls.append(url)
        return png

    monkeypatch.setattr(api, "_download", fake_download)

    first = api.pokemon_sprite({"id": 1, "sprite_url": "https://img.test/1.png"})
    second = api.pokemon_sprite({"id": 1, "sprite_url": "https://img.test/1.png"})

    assert first == sprite_dir / "1.png"
    assert second == first
    assert first.read_bytes() == png
    assert len(calls) == 1
    assert list(sprite_dir.iterdir()) == [first]


def test_sprite_without_url_returns_none(api_dirs, monkeypatch):
    monkeypatch.setattr(api, "_download", lambda url: pytest.fail("não deveria baixar"))

    assert api.pokemon_sprite({"id": 1, "sprite_url": None}) is None


def test_sprite_rejects_non_png_content(api_dirs, monkeypatch):
    _, sprite_dir = api_dirs
    monkeypatch.setattr(api, "_download", lambda url: b"<html>erro</html>")

    with pytest.raises(api.PokeApiError, match="imagem"):
        api.pokemon_sprite({"id": 1, "sprite_url": "https://img.test/1.png"})

    assert not (sprite_dir / "1.png").exists()


def test_corrupted_sprite_in_cache_is_downloaded_again(api_dirs, monkeypatch):
    _, sprite_dir = api_dirs
    sprite_dir.mkdir(parents=True)
    (sprite_dir / "1.png").write_bytes(b"lixo")
    png = api.PNG_SIGNATURE + b"novo"
    calls = []

    def fake_download(url):
        calls.append(url)
        return png

    monkeypatch.setattr(api, "_download", fake_download)

    result = api.pokemon_sprite({"id": 1, "sprite_url": "https://img.test/1.png"})

    assert result == sprite_dir / "1.png"
    assert result.read_bytes() == png
    assert len(calls) == 1


def test_compact_payload_without_sprites_has_no_sprite_url():
    payload = _payload()
    del payload["sprites"]

    compact = api._compact_payload(payload)

    assert compact["sprite_url"] is None
