import re

from src.pokedex_app import theme


def test_stylesheet_replaces_every_color_token():
    css = theme.stylesheet()

    assert not re.search(r"@[a-z_]+", css)
    assert theme.COLORS["background"] in css
    assert theme.COLORS["accent"] in css


def test_style_file_only_references_known_colors():
    tokens = set(re.findall(r"@([a-z_]+)", theme.STYLE_FILE.read_text(encoding="utf-8")))

    assert tokens
    assert tokens <= set(theme.COLORS)


def test_stylesheet_falls_back_when_file_is_missing(tmp_path):
    css = theme.stylesheet(tmp_path / "nao_existe.qss")

    assert not re.search(r"@[a-z_]+", css)
    assert theme.COLORS["text"] in css


def test_type_colors_cover_the_eighteen_types():
    assert len(theme.TYPE_COLORS) == 18
    assert theme.TYPE_COLORS["grass"] == "#7AC74C"
