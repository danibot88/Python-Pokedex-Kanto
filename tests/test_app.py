import pytest
from src.pokedex_app import app as app_module
from src.pokedex_app import storage
from src.pokedex_app.api import PokeApiError


def _details(number: int) -> dict:
    return {
        "schema": 2,
        "id": number,
        "name": f"pokemon-{number}",
        "height": 0.7,
        "weight": 6.9,
        "types": ["grass", "poison"],
        "abilities": ["overgrow"],
        "stats": {"hp": 250, "attack": 49},
        "sprite_url": None,
    }


@pytest.fixture
def make_window(qapp, monkeypatch):
    windows = []

    def factory(loader=None, sprite_loader=None):
        if loader is None:

            def default_loader(number):
                return _details(number)

            loader = default_loader

        if sprite_loader is None:

            def default_sprite_loader(details):
                return None

            sprite_loader = default_sprite_loader

        monkeypatch.setattr(app_module, "pokemon_details", loader)
        monkeypatch.setattr(app_module, "pokemon_sprite", sprite_loader)

        window = app_module.MainWindow()
        window.show()
        assert window.thread_pool.waitForDone(5000)
        qapp.processEvents()
        windows.append(window)
        return window

    yield factory

    for window in windows:
        window.close()
        window.deleteLater()
    qapp.processEvents()


def test_window_loads_first_pokemon(make_window):
    window = make_window()

    assert window.name_label.text() == "Bulbasaur"
    assert window.number_label.text() == "#001"
    assert window.stats_box.count() == 2
    assert window._loaded_number == 1
    assert window._workers == {}


def test_stat_bars_use_full_base_stat_range(make_window):
    window = make_window()

    hp_row = window.stats_box.itemAt(0).widget()
    assert hp_row.bar.maximum() == app_module.MAX_BASE_STAT
    assert hp_row.bar.maximum() == 255
    assert hp_row.bar.value() == 250


def test_stats_keep_canonical_order():
    stats = {"speed": 45, "hp": 250, "special-attack": 65, "attack": 49}

    assert app_module.ordered_stats(stats) == [
        ("hp", 250),
        ("attack", 49),
        ("special-attack", 65),
        ("speed", 45),
    ]


def test_selecting_the_same_pokemon_does_not_reload(make_window, monkeypatch):
    calls = []

    def loader(number):
        calls.append(number)
        return _details(number)

    window = make_window(loader)
    assert calls == [1]

    window._selection_changed(window.list_widget.item(0), None)

    assert calls == [1]


def test_filtering_the_list_does_not_reload(make_window):
    calls = []

    def loader(number):
        calls.append(number)
        return _details(number)

    window = make_window(loader)

    window.search.setText("bulba")

    assert calls == [1]
    assert window.list_widget.count() == 1


def test_toggling_favorite_does_not_reload(make_window):
    calls = []

    def loader(number):
        calls.append(number)
        return _details(number)

    window = make_window(loader)

    window._toggle_favorite()

    assert calls == [1]
    assert window.favorite_button.text().startswith("★")
    assert storage.load_favorites() == {1}


def test_stale_response_is_ignored(make_window, qapp):
    window = make_window()

    window.list_widget.setCurrentRow(1)
    assert window.stats_box.count() == 0

    window._details_loaded(1, _details(1), None)

    assert window.stats_box.count() == 0
    assert window.name_label.text() == "Ivysaur"

    assert window.thread_pool.waitForDone(5000)
    qapp.processEvents()

    assert window.stats_box.count() == 2
    assert window._loaded_number == 2


def test_error_from_api_is_shown_to_the_user(make_window):
    def failing_loader(number):
        raise PokeApiError("Sem conexão de teste.")

    window = make_window(failing_loader)

    assert window.status.text() == "Sem conexão de teste."
    assert window.status.toolTip() == "Sem conexão de teste."
    assert window.artwork.text() == "Imagem indisponível"
    assert window._loaded_number is None
    assert window._workers == {}


def test_missing_sprite_shows_placeholder(make_window):
    window = make_window()

    assert window.artwork.text() == "Imagem indisponível"


def test_sprite_failure_still_shows_details(make_window):
    def failing_sprite(details):
        raise PokeApiError("imagem fora do ar")

    window = make_window(sprite_loader=failing_sprite)

    assert window._loaded_number == 1
    assert window.stats_box.count() == 2
    assert window.artwork.text() == "Imagem indisponível"


def test_details_renders_types_and_measurements(make_window):
    window = make_window()

    assert "GRASS" in window.types.text()
    assert "POISON" in window.types.text()
    assert "Altura: 0.7 m" in window.measurements.text()
    assert "Peso: 6.9 kg" in window.measurements.text()
    assert window.abilities.text() == "Habilidades: Overgrow"


def test_reloading_after_failure_retries(make_window):
    attempts = []

    def flaky_loader(number):
        attempts.append(number)
        if len(attempts) == 1:
            raise PokeApiError("Falha temporária.")
        return _details(number)

    window = make_window(flaky_loader)
    assert window._loaded_number is None

    window._selection_changed(window.list_widget.item(0), None)
    assert window.thread_pool.waitForDone(5000)

    assert len(attempts) == 2
