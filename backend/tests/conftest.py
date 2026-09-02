"""Configuração comum dos testes.

O redirecionamento de `INCIPIT_DATA_DIR` acontece no topo do módulo, ANTES de
qualquer import de `incipit`: `incipit.config` lê a variável no import e a
congela em constantes de módulo. Se um teste importasse `incipit` primeiro, o
cache de áudio e os modelos iriam parar no diretório real do usuário.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_DATA_DIR = Path(tempfile.mkdtemp(prefix="incipit-tests-"))
os.environ["INCIPIT_DATA_DIR"] = str(_DATA_DIR)

import pytest  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help="Regrava os JSONs de backend/tests/golden/ a partir do código atual.",
    )


@pytest.fixture(scope="session")
def update_goldens(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--update-goldens"))


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Diretório temporário para onde `incipit.config` foi apontado."""
    return _DATA_DIR


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Os testes de contrato usam `httpx.ASGITransport`, que só é assíncrono."""
    return "asyncio"
