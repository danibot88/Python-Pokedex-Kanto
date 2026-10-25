import logging
import sys
from logging.handlers import RotatingFileHandler

import pytest
from src.pokedex_app import log


@pytest.fixture
def root_handlers():
    root = logging.getLogger()
    before = list(root.handlers)
    original_level = root.level
    yield before
    for handler in list(root.handlers):
        if handler not in before:
            root.removeHandler(handler)
            handler.close()
    root.setLevel(original_level)


def test_setup_logging_writes_messages_from_package_modules(tmp_path, monkeypatch, root_handlers):
    log_file = tmp_path / "app.log"
    monkeypatch.setattr(log, "LOG_FILE", log_file)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    log.setup_logging(logging.INFO)
    logging.getLogger("src.pokedex_app.api").warning("mensagem de teste")

    for handler in logging.getLogger().handlers:
        handler.flush()

    content = log_file.read_text(encoding="utf-8")
    assert "mensagem de teste" in content
    assert "src.pokedex_app.api" in content


def test_setup_logging_is_idempotent(tmp_path, monkeypatch, root_handlers):
    monkeypatch.setattr(log, "LOG_FILE", tmp_path / "app.log")
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    log.setup_logging(logging.INFO)
    log.setup_logging(logging.INFO)

    handlers = [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, RotatingFileHandler)
    ]
    assert len(handlers) == 1


def test_install_excepthook_logs_and_calls_callback(root_handlers, caplog):
    calls = []
    log.install_excepthook(lambda: calls.append(True))

    try:
        raise RuntimeError("falha simulada")
    except RuntimeError:
        sys.excepthook(*sys.exc_info())
    finally:
        sys.excepthook = sys.__excepthook__

    assert calls == [True]
    assert "falha simulada" in caplog.text
