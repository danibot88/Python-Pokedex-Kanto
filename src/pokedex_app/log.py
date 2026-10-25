"""Configuração de logging e captura de erros não tratados."""

import logging
import sys
from collections.abc import Callable
from logging.handlers import RotatingFileHandler

from .storage import LOG_DIR, prepare_directories

LOG_FILE = LOG_DIR / "app.log"
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
MAX_LOG_BYTES = 512 * 1024
LOG_BACKUPS = 3

logger = logging.getLogger("pokedex")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configura o logger raiz para gravar em arquivo.

    O handler fica no logger raiz para capturar também os módulos
    ``src.pokedex_app.*``, que não são filhos de ``pokedex``.
    """
    root = logging.getLogger()
    root.setLevel(level)
    if any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        return logger

    try:
        prepare_directories()
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=MAX_LOG_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8"
        )
    except OSError as exc:
        logger.warning("Não foi possível abrir o arquivo de log: %s", exc)
        return logger

    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(file_handler)

    if not getattr(sys, "frozen", False) and sys.stderr is not None:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(stream_handler)

    return logger


def install_excepthook(on_error: Callable[[], None] | None = None) -> None:
    """Registra um hook que loga e avisa o usuário sobre erros inesperados."""

    def handle(exc_type, exc_value, exc_tb) -> None:
        logger.critical("Erro não tratado", exc_info=(exc_type, exc_value, exc_tb))
        if on_error is None:
            return
        try:
            on_error()
        except Exception:
            logger.exception("Falha ao exibir a mensagem de erro para o usuário")

    sys.excepthook = handle
