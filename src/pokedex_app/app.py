import sys

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .api import PokeApiError, pokemon_details, pokemon_sprite
from .data import all_pokemon
from .log import LOG_FILE, get_logger, install_excepthook, setup_logging
from .paths import ASSETS_DIR
from .storage import load_favorites, prepare_directories, save_favorites
from .theme import BADGE_TEXT, COLORS, TYPE_COLORS, stylesheet

logger = get_logger(__name__)

MAX_BASE_STAT = 255

# Ordem canônica dos atributos na PokéAPI (dicts não preservam ordem ao
# atravessar sinais do Qt, então ordenamos explicitamente).
STAT_ORDER = (
    "hp",
    "attack",
    "defense",
    "special-attack",
    "special-defense",
    "speed",
)


class WorkerSignals(QObject):
    # ``object`` evita a conversão para QVariantMap, que ordena as chaves.
    loaded = Signal(int, object, object)
    failed = Signal(int, str)
    finished = Signal(int)


def ordered_stats(stats: dict) -> list[tuple[str, int]]:
    """Devolve os atributos na ordem canônica, mantendo extras ao final."""
    ordered = [(name, stats[name]) for name in STAT_ORDER if name in stats]
    extras = [(name, value) for name, value in stats.items() if name not in STAT_ORDER]
    return ordered + extras


class DetailsWorker(QRunnable):
    """Busca os dados de um Pokémon sem bloquear a interface."""

    def __init__(self, number: int, token: int):
        super().__init__()
        self.number = number
        self.token = token
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            details = pokemon_details(self.number)
            try:
                sprite = pokemon_sprite(details)
            except (PokeApiError, OSError, ValueError) as exc:
                logger.warning("Imagem indisponível para o Pokémon #%03d: %s", self.number, exc)
                sprite = None
        except (PokeApiError, OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Falha ao carregar o Pokémon #%03d: %s", self.number, exc)
            self.signals.failed.emit(self.token, str(exc))
        except Exception:
            logger.exception("Erro inesperado ao carregar o Pokémon #%03d", self.number)
            self.signals.failed.emit(self.token, "Erro inesperado ao carregar os dados.")
        else:
            self.signals.loaded.emit(self.token, details, sprite)
        finally:
            self.signals.finished.emit(self.token)


class StatRow(QWidget):
    def __init__(self, label: str, value: int):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        name = QLabel(label.replace("special-", "sp. ").upper())
        name.setMinimumWidth(85)
        name.setObjectName("muted")
        self.bar = QProgressBar()
        self.bar.setRange(0, MAX_BASE_STAT)
        self.bar.setValue(value)
        self.bar.setFormat(str(value))
        layout.addWidget(name)
        layout.addWidget(self.bar)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        prepare_directories()
        self.pokemon = all_pokemon()
        self.favorites = load_favorites()
        self.current_number = 1
        self._loaded_number: int | None = None
        self._request_token = 0
        self._workers: dict[int, DetailsWorker] = {}
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle("Pokédex Kanto")
        self.setMinimumSize(980, 650)
        self.resize(1180, 760)
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "pokeball.svg")))
        self._build_ui()
        self._apply_style()
        self._fill_list()
        self.list_widget.setCurrentRow(0)

    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(330)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 20, 22, 20)
        logo = QLabel("POKÉDEX")
        logo.setObjectName("logo")
        subtitle = QLabel("REGIÃO DE KANTO  •  001—151")
        subtitle.setObjectName("muted")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por nome ou número…")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Buscar Pokémon")
        self.search.textChanged.connect(self._fill_list)
        self.only_favorites = QCheckBox("Mostrar somente favoritos")
        self.only_favorites.toggled.connect(self._fill_list)
        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName("Lista de Pokémon")
        self.list_widget.currentItemChanged.connect(self._selection_changed)
        side.addWidget(logo)
        side.addWidget(subtitle)
        side.addSpacing(12)
        side.addWidget(self.search)
        side.addWidget(self.only_favorites)
        side.addWidget(self.list_widget, 1)

        content = QScrollArea()
        content.setWidgetResizable(True)
        content.setFrameShape(QFrame.NoFrame)
        page = QWidget()
        self.detail_layout = QVBoxLayout(page)
        self.detail_layout.setContentsMargins(48, 34, 48, 40)
        self.detail_layout.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        self.number_label = QLabel("#001")
        self.number_label.setObjectName("number")
        self.name_label = QLabel("Bulbasaur")
        self.name_label.setObjectName("name")
        self.favorite_button = QPushButton("☆  Adicionar aos favoritos")
        self.favorite_button.setObjectName("favorite")
        self.favorite_button.clicked.connect(self._toggle_favorite)
        title_box.addWidget(self.number_label)
        title_box.addWidget(self.name_label)
        title_box.addWidget(self.favorite_button, alignment=Qt.AlignLeft)
        self.artwork = QLabel("Selecione um Pokémon")
        self.artwork.setObjectName("artwork")
        self.artwork.setAlignment(Qt.AlignCenter)
        self.artwork.setFixedSize(330, 300)
        header.addLayout(title_box, 1)
        header.addWidget(self.artwork)

        self.status = QLabel("Carregando informações…")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        self.types = QLabel()
        self.types.setObjectName("types")
        self.measurements = QLabel()
        self.abilities = QLabel()
        self.abilities.setWordWrap(True)
        section = QLabel("ATRIBUTOS BASE")
        section.setObjectName("section")
        self.stats_box = QVBoxLayout()

        self.detail_layout.addLayout(header)
        self.detail_layout.addWidget(self.status)
        self.detail_layout.addWidget(self.types)
        self.detail_layout.addWidget(self.measurements)
        self.detail_layout.addWidget(self.abilities)
        self.detail_layout.addSpacing(12)
        self.detail_layout.addWidget(section)
        self.detail_layout.addLayout(self.stats_box)
        self.detail_layout.addStretch()
        content.setWidget(page)
        root.addWidget(sidebar)
        root.addWidget(content, 1)
        self.setCentralWidget(central)

    def _apply_style(self):
        self.setStyleSheet(stylesheet())

    def _fill_list(self):
        current = self.current_number
        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        favorites_only = (
            self.only_favorites.isChecked() if hasattr(self, "only_favorites") else False
        )
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        chosen_row = -1
        for pokemon in self.pokemon:
            if favorites_only and pokemon["id"] not in self.favorites:
                continue
            haystack = f"{pokemon['id']} {pokemon['name'].lower()} {pokemon['api_name']}"
            if query and query not in haystack:
                continue
            star = "★" if pokemon["id"] in self.favorites else " "
            item = QListWidgetItem(f"{star}  #{pokemon['id']:03d}   {pokemon['name']}")
            item.setData(Qt.UserRole, pokemon)
            self.list_widget.addItem(item)
            if pokemon["id"] == current:
                chosen_row = self.list_widget.count() - 1
        self.list_widget.blockSignals(False)
        if chosen_row >= 0:
            self.list_widget.setCurrentRow(chosen_row)

    def _selection_changed(self, current, _previous):
        if current is None:
            return
        pokemon = current.data(Qt.UserRole)
        if not isinstance(pokemon, dict):
            return

        number = pokemon["id"]
        if number == self.current_number and self._loaded_number == number:
            # A lista foi reconstruída (busca/favoritos): nada mudou de fato.
            return

        self.current_number = number
        self._loaded_number = None
        self.number_label.setText(f"#{number:03d}")
        self.name_label.setText(pokemon["name"])
        self.artwork.setPixmap(QPixmap())
        self.artwork.setToolTip("")
        self.artwork.setText("Carregando…")
        self.status.setText("Buscando dados locais ou sincronizando com a PokéAPI…")
        self.status.setToolTip("")
        self.types.clear()
        self.measurements.clear()
        self.abilities.clear()
        self._clear_stats()
        self._update_favorite_button()
        self._fetch_details(number)

    def _fetch_details(self, number: int) -> None:
        self._request_token += 1
        token = self._request_token
        worker = DetailsWorker(number, token)
        worker.signals.loaded.connect(self._details_loaded)
        worker.signals.failed.connect(self._details_failed)
        worker.signals.finished.connect(self._worker_finished)
        self._workers[token] = worker
        self.thread_pool.start(worker)

    def _worker_finished(self, token: int) -> None:
        self._workers.pop(token, None)

    def _details_loaded(self, token: int, details: dict, sprite):
        if token != self._request_token:
            logger.debug("Ignorando resposta obsoleta do Pokémon #%03d", details.get("id", 0))
            return

        self._loaded_number = details["id"]
        self.status.setText("Dados armazenados localmente para os próximos acessos.")
        badges = []
        for kind in details["types"]:
            color = TYPE_COLORS.get(kind, COLORS["accent"])
            badges.append(
                f"<span style='background:{color}; color:{BADGE_TEXT}; padding:5px 10px;"
                f" font-weight:700;'>{kind.upper()}</span>"
            )
        self.types.setText("  ".join(badges))
        self.measurements.setText(
            f"Altura: {details['height']:.1f} m     •     Peso: {details['weight']:.1f} kg"
        )
        abilities = ", ".join(name.replace("-", " ").title() for name in details["abilities"])
        self.abilities.setText(f"Habilidades: {abilities}")
        self._clear_stats()
        for name, value in ordered_stats(details["stats"]):
            self.stats_box.addWidget(StatRow(name, value))
        self._show_artwork(sprite)

    def _show_artwork(self, sprite) -> None:
        pixmap = QPixmap(str(sprite)) if sprite else QPixmap()
        if pixmap.isNull():
            if sprite:
                logger.warning(
                    "Imagem inválida para o Pokémon #%03d: %s", self.current_number, sprite
                )
            self.artwork.setPixmap(QPixmap())
            self.artwork.setText("Imagem indisponível")
            return
        self.artwork.setPixmap(pixmap.scaled(280, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _details_failed(self, token: int, message: str) -> None:
        if token != self._request_token:
            return
        self._loaded_number = None
        logger.warning(
            "Detalhes indisponíveis para o Pokémon #%03d: %s", self.current_number, message
        )
        self.status.setText(message)
        self.status.setToolTip(message)
        self.artwork.setPixmap(QPixmap())
        self.artwork.setText("Imagem indisponível")

    def _clear_stats(self):
        while self.stats_box.count():
            item = self.stats_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _toggle_favorite(self):
        if self.current_number in self.favorites:
            self.favorites.remove(self.current_number)
        else:
            self.favorites.add(self.current_number)
        save_favorites(self.favorites)
        self._update_favorite_button()
        self._fill_list()

    def _update_favorite_button(self):
        favorite = self.current_number in self.favorites
        self.favorite_button.setText(
            "★  Remover dos favoritos" if favorite else "☆  Adicionar aos favoritos"
        )


def _report_unexpected_error() -> None:
    QMessageBox.critical(
        None,
        "Pokédex Kanto",
        f"Ocorreu um erro inesperado.\n\nDetalhes salvos em:\n{LOG_FILE}",
    )


def run() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Pokédex Kanto")
    app.setOrganizationName("PokedexKanto")
    app.setApplicationVersion(__version__)
    app.setFont(QFont("Segoe UI", 10))
    install_excepthook(_report_unexpected_error)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    logger.info("Aplicativo encerrado com código %s", exit_code)
    return exit_code
