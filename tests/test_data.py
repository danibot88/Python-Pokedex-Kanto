from src.pokedex_app.data import all_pokemon


def test_returns_all_151_kanto_pokemon():
    pokemon = all_pokemon()

    assert len(pokemon) == 151
    assert [item["id"] for item in pokemon] == list(range(1, 152))


def test_api_names_are_lowercase_without_spaces():
    for pokemon in all_pokemon():
        api_name = pokemon["api_name"]
        assert api_name == api_name.lower()
        assert " " not in api_name


def test_api_names_match_pokeapi_slugs():
    by_id = {item["id"]: item for item in all_pokemon()}

    assert by_id[1]["api_name"] == "bulbasaur"
    assert by_id[29]["api_name"] == "nidoran-f"
    assert by_id[32]["api_name"] == "nidoran-m"
    assert by_id[83]["api_name"] == "farfetchd"
    assert by_id[122]["api_name"] == "mr-mime"
    assert by_id[151]["api_name"] == "mew"


def test_display_names_are_humanized():
    by_id = {item["id"]: item for item in all_pokemon()}

    assert by_id[29]["name"] == "Nidoran ♀"
    assert by_id[32]["name"] == "Nidoran ♂"
    assert by_id[83]["name"] == "Farfetch’d"
    assert by_id[122]["name"] == "Mr. Mime"
    assert by_id[25]["name"] == "Pikachu"


def test_display_names_are_unique():
    names = [item["name"] for item in all_pokemon()]

    assert len(names) == len(set(names))
