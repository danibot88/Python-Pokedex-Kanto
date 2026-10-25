import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Diretório de dados isolado: nada é escrito em %LOCALAPPDATA% durante os testes.
DATA_DIR = Path(tempfile.mkdtemp(prefix="pokedex-tests-"))
os.environ["POKEDEX_APP_DIR"] = str(DATA_DIR)
# Permite rodar os testes de interface sem servidor gráfico.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
atexit.register(shutil.rmtree, DATA_DIR, ignore_errors=True)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
