import logging
import re
from pathlib import Path

from .paths import ASSETS_DIR

logger = logging.getLogger(__name__)

COLORS = {
    "background": "#101318",
    "panel": "#181d25",
    "panel_alt": "#202733",
    "text": "#f4f7fb",
    "muted": "#9ba7b7",
    "accent": "#ef4056",
    "accent_dark": "#b92740",
    "line": "#303947",
}

TYPE_COLORS = {
    "normal": "#A8A77A",
    "fire": "#EE8130",
    "water": "#6390F0",
    "electric": "#F7D02C",
    "grass": "#7AC74C",
    "ice": "#96D9D6",
    "fighting": "#C22E28",
    "poison": "#A33EA1",
    "ground": "#E2BF65",
    "flying": "#A98FF3",
    "psychic": "#F95587",
    "bug": "#A6B91A",
    "rock": "#B6A136",
    "ghost": "#735797",
    "dragon": "#6F35FC",
    "dark": "#705746",
    "steel": "#B7B7CE",
    "fairy": "#D685AD",
}

BADGE_TEXT = "#101318"

STYLE_FILE = ASSETS_DIR / "style.qss"
_FALLBACK_TEMPLATE = "QWidget { background: @background; color: @text; }"


def stylesheet(path: Path | None = None) -> str:
    """Lê o QSS e substitui os marcadores ``@cor`` pelos valores de COLORS."""
    style_path = path or STYLE_FILE
    try:
        template = style_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Não foi possível ler %s (%s); usando estilo mínimo.", style_path, exc)
        template = _FALLBACK_TEMPLATE

    for name, value in COLORS.items():
        template = template.replace(f"@{name}", value)

    leftover = sorted(set(re.findall(r"@[a-z_]+", template)))
    if leftover:
        logger.warning("Marcadores de cor desconhecidos no QSS: %s", ", ".join(leftover))
    return template
