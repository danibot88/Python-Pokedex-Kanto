import sys
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from .api import PokeApiError, pokemon_details, pokemon_sprite
from .data import all_pokemon
from .storage import load_favorites, prepare_directories, save_favorites
from .theme import COLORS, TYPE_COLORS


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"


class WorkerSignals(QObject):
    loaded = Signal(dict, object)
    failed = Signal(str)


class DetailsWorker(QRunnable):
    def __init__(self, number: int):
        super().__init__()
        self.number = number
        self.signals = WorkerSignals()

    def run(self):
        try:
            details = pokemon_details(self.number)
            sprite = pokemon_sprite(details)
            self.signals.loaded.emit(details, sprite)
        except (PokeApiError, OSError, ValueError) as exc:
            self.signals.failed.emit(str(exc))


class StatRow(QWidget):
    def __init__(self, label: str, value: int):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        name = QLabel(label.replace("special-", "sp. ").upper())
        name.setFixedWidth(85)
        name.setObjectName("muted")
        bar = QProgressBar()
        bar.setRange(0, 180)
        bar.setValue(value)
        bar.setFormat(str(value))
        layout.addWidget(name)
        layout.addWidget(bar)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        prepare_directories()
        self.pokemon = all_pokemon()
        self.favorites = load_favorites()
        self.current_number = 1
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle("Pokédex Kanto")
        self.setMinimumSize(980, 650)
        self.resize(1180, 760)
        self.setWindowIcon(QIcon(str(ASSETS / "pokeball.svg")))
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
        self.search.textChanged.connect(self._fill_list)
        self.only_favorites = QCheckBox("Mostrar somente favoritos")
        self.only_favorites.toggled.connect(self._fill_list)
        self.list_widget = QListWidget()
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
        self.types = QLabel()
        self.types.setObjectName("types")
        self.measurements = QLabel()
        self.abilities = QLabel()
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
        self.setStyleSheet(f"""
            * {{ color: {COLORS['text']}; font-family: 'Segoe UI'; font-size: 14px; }}
            QMainWindow, QWidget {{ background: {COLORS['background']}; }}
            #sidebar {{ background: {COLORS['panel']}; border-right: 1px solid {COLORS['line']}; }}
            #logo {{ color: {COLORS['accent']}; font-size: 29px; font-weight: 900; letter-spacing: 2px; }}
            #muted, #number {{ color: {COLORS['muted']}; }}
            #number {{ font-size: 18px; font-weight: 700; }}
            #name {{ font-size: 44px; font-weight: 800; }}
            #section {{ color: {COLORS['accent']}; font-weight: 800; letter-spacing: 1px; }}
            #artwork {{ background: {COLORS['panel']}; border: 1px solid {COLORS['line']}; border-radius: 22px; }}
            QLineEdit {{ background: {COLORS['panel_alt']}; border: 1px solid {COLORS['line']}; border-radius: 9px; padding: 10px; }}
            QListWidget {{ background: transparent; border: 0; outline: 0; }}
            QListWidget::item {{ padding: 10px; margin: 2px 0; border-radius: 8px; }}
            QListWidget::item:selected {{ background: {COLORS['accent']}; }}
            QPushButton#favorite {{ background: {COLORS['panel_alt']}; border: 1px solid {COLORS['line']}; border-radius: 9px; padding: 9px 13px; }}
            QPushButton#favorite:hover {{ border-color: {COLORS['accent']}; }}
            QProgressBar {{ background: {COLORS['panel_alt']}; border: 0; border-radius: 7px; height: 15px; text-align: center; }}
            QProgressBar::chunk {{ background: {COLORS['accent']}; border-radius: 7px; }}
            QScrollBar:vertical {{ background: transparent; width: 9px; }}
            QScrollBar::handle:vertical {{ background: {COLORS['line']}; border-radius: 4px; min-height: 35px; }}
        """)

    def _fill_list(self):
        current = self.current_number
        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        favorites_only = self.only_favorites.isChecked() if hasattr(self, "only_favorites") else False
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
        self.current_number = pokemon["id"]
        self.number_label.setText(f"#{pokemon['id']:03d}")
        self.name_label.setText(pokemon["name"])
        self.artwork.setPixmap(QPixmap())
        self.artwork.setText("Carregando…")
        self.status.setText("Buscando dados locais ou sincronizando com a PokéAPI…")
        self.types.clear()
        self.measurements.clear()
        self.abilities.clear()
        self._clear_stats()
        self._update_favorite_button()
        worker = DetailsWorker(pokemon["id"])
        worker.signals.loaded.connect(self._details_loaded)
        worker.signals.failed.connect(self._details_failed)
        self.thread_pool.start(worker)

    def _details_loaded(self, details: dict, sprite):
        if details["id"] != self.current_number:
            return
        self.status.setText("Dados armazenados localmente para os próximos acessos.")
        badges = []
        for kind in details["types"]:
            color = TYPE_COLORS.get(kind, COLORS["accent"])
            badges.append(f"<span style='background:{color}; color:#101318; padding:5px 10px; font-weight:700;'>{kind.upper()}</span>")
        self.types.setText("  ".join(badges))
        self.measurements.setText(f"Altura: {details['height']:.1f} m     •     Peso: {details['weight']:.1f} kg")
        abilities = ", ".join(name.replace("-", " ").title() for name in details["abilities"])
        self.abilities.setText(f"Habilidades: {abilities}")
        for name, value in details["stats"].items():
            self.stats_box.addWidget(StatRow(name, value))
        if sprite:
            pixmap = QPixmap(str(sprite)).scaled(280, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.artwork.setPixmap(pixmap)
            self.artwork.setText("")

    def _details_failed(self, message: str):
        self.status.setText("Sem dados em cache. Conecte-se à internet e selecione novamente.")
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
        self.favorite_button.setText("★  Remover dos favoritos" if favorite else "☆  Adicionar aos favoritos")


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pokédex Kanto")
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    return app.exec()

