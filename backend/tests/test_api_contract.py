"""Contrato HTTP das 7 rotas de hoje, exercido via `httpx.ASGITransport`.

Este é o teste que mais importa neste repo. O app não fala com o backend por
IPC do Tauri: `app/src/api.ts` faz `fetch` puro contra 127.0.0.1:8765. Ou seja,
a fronteira entre as duas metades é HTTP, e a maior parte dos bugs de
integração do incipit é um campo que mudou de nome ou um status que mudou de
número — não um bug de componente React nem de módulo Rust.

Por isso as asserções são sobre o *shape de hoje*: nomes de campo, códigos de
status e cabeçalhos, do jeito que `api.ts` os consome agora.

Nenhum teste aqui sintetiza áudio de verdade. Um engine de mentira substitui o
Piper (que baixaria ~60 MB de modelo na primeira chamada) — o que este arquivo
prova é o contrato HTTP, não a qualidade do áudio.
"""

from __future__ import annotations

import struct
import threading
import time
import wave
from io import BytesIO

import httpx
import pytest

from incipit import api as api_mod
from incipit.tts import cache as tts_cache
from incipit.tts import pregen

from .conftest import FIXTURES

pytestmark = pytest.mark.anyio


# --------------------------------------------------------------------------- #
# Infra
# --------------------------------------------------------------------------- #
def _wav_bytes(seconds: float = 0.05, rate: int = 22050) -> bytes:
    """WAV PCM 16-bit mono — o mesmo formato que os engines de verdade devolvem."""
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<h", 0) * int(rate * seconds))
    return buf.getvalue()


class FakeEngine:
    """Engine instantâneo. `gate`, se dado, segura a síntese até o teste soltar."""

    def __init__(self, gate: threading.Event | None = None) -> None:
        self.calls: list[str] = []
        self.gate = gate

    def synthesize(self, text, *, voice=None, language="pt", speed=1.0) -> bytes:
        if self.gate is not None:
            self.gate.wait(timeout=5)
        self.calls.append(text)
        return _wav_bytes()


@pytest.fixture
def client() -> httpx.AsyncClient:
    from main import app

    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


@pytest.fixture
def fake_engine(monkeypatch: pytest.MonkeyPatch) -> FakeEngine:
    """Troca o engine nos DOIS pontos de uso. `get_engine` está memoizado com
    `lru_cache`, então trocar o nome no namespace de cada módulo é o que
    realmente evita carregar o modelo — mexer no cache não bastaria."""
    engine = FakeEngine()
    monkeypatch.setattr(api_mod, "get_engine", lambda name: engine)
    monkeypatch.setattr(pregen, "get_engine", lambda name: engine)
    return engine


def _wait_for(predicate, timeout: float = 5.0, interval: float = 0.01):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return None


# --------------------------------------------------------------------------- #
# /health
# --------------------------------------------------------------------------- #
async def test_health(client: httpx.AsyncClient) -> None:
    """O app faz polling desta rota para saber se o sidecar subiu."""
    async with client as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# --------------------------------------------------------------------------- #
# /extract
# --------------------------------------------------------------------------- #
async def test_extract_returns_book_shape(client: httpx.AsyncClient) -> None:
    async with client as c:
        r = await c.post("/extract", json={"path": str(FIXTURES / "com-outline.pdf")})

    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"title", "author", "source_format", "chapters"}
    assert body["source_format"] == "pdf"
    assert body["title"] == "A casa de treze janelas"

    chapter = body["chapters"][0]
    assert set(chapter) == {"index", "title", "paragraphs"}
    assert set(chapter["paragraphs"][0]) == {"index", "text"}

    # `paragraph_count` é @property, não campo — não deve aparecer no JSON.
    assert "paragraph_count" not in body


async def test_extract_epub_returns_book_shape(client: httpx.AsyncClient) -> None:
    async with client as c:
        r = await c.post(
            "/extract", json={"path": str(FIXTURES / "paragrafos-simples.epub")}
        )
    assert r.status_code == 200
    assert r.json()["source_format"] == "epub"


async def test_extract_missing_file_is_404(client: httpx.AsyncClient) -> None:
    async with client as c:
        r = await c.post("/extract", json={"path": str(FIXTURES / "nao-existe.pdf")})
    assert r.status_code == 404
    assert "detail" in r.json()


async def test_extract_unsupported_format_is_400(client: httpx.AsyncClient) -> None:
    async with client as c:
        r = await c.post("/extract", json={"path": str(FIXTURES / "make_fixtures.py")})
    assert r.status_code == 400
    assert "Formato não suportado" in r.json()["detail"]


async def test_extract_requires_path(client: httpx.AsyncClient) -> None:
    """Corpo inválido é 422 do pydantic, não 400 nosso."""
    async with client as c:
        r = await c.post("/extract", json={})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# /tts/engines
# --------------------------------------------------------------------------- #
async def test_tts_engines(client: httpx.AsyncClient) -> None:
    async with client as c:
        r = await c.get("/tts/engines")
    assert r.status_code == 200
    assert r.json() == {"engines": ["piper", "xtts"]}


# --------------------------------------------------------------------------- #
# /tts
# --------------------------------------------------------------------------- #
async def test_tts_returns_wav_and_cache_headers(
    client: httpx.AsyncClient, fake_engine: FakeEngine
) -> None:
    """Primeira chamada é miss e sintetiza; a segunda é hit e NÃO sintetiza.
    O X-Cache é o que permite ver, de fora, se o cache progressivo está de pé."""
    payload = {
        "text": "Uma frase que ainda nao foi sintetizada nesta sessao.",
        "engine": "piper",
        "voice": "pt_BR-faber-medium",
        "language": "pt",
        "speed": 1.0,
    }
    expected_key = tts_cache.cache_key(
        payload["engine"], payload["text"], payload["voice"],
        payload["language"], payload["speed"],
    )

    async with client as c:
        first = await c.post("/tts", json=payload)
        second = await c.post("/tts", json=payload)

    assert first.status_code == 200
    assert first.headers["content-type"] == "audio/wav"
    assert first.headers["x-cache"] == "miss"
    assert first.headers["x-cache-key"] == expected_key
    assert first.content.startswith(b"RIFF")

    assert second.status_code == 200
    assert second.headers["x-cache"] == "hit"
    assert second.headers["x-cache-key"] == expected_key
    assert second.content == first.content

    assert fake_engine.calls == [payload["text"]], "o hit não pode sintetizar de novo"
    assert tts_cache.cache_path(expected_key).is_file()


async def test_tts_defaults_are_applied(
    client: httpx.AsyncClient, fake_engine: FakeEngine
) -> None:
    """Só `text` é obrigatório; engine/idioma/velocidade têm padrão no modelo."""
    async with client as c:
        r = await c.post("/tts", json={"text": "Somente o texto."})
    assert r.status_code == 200
    assert r.headers["x-cache-key"] == tts_cache.cache_key(
        "piper", "Somente o texto.", None, "pt", 1.0
    )


async def test_tts_strips_text_before_hashing(
    client: httpx.AsyncClient, fake_engine: FakeEngine
) -> None:
    """O endpoint faz `.strip()` antes de gerar a chave — espaço solto vindo do
    parágrafo extraído não pode furar o cache."""
    async with client as c:
        a = await c.post("/tts", json={"text": "  frase com espaco  "})
        b = await c.post("/tts", json={"text": "frase com espaco"})
    assert a.headers["x-cache-key"] == b.headers["x-cache-key"]


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
async def test_tts_empty_text_is_400(client: httpx.AsyncClient, text: str) -> None:
    async with client as c:
        r = await c.post("/tts", json={"text": text})
    assert r.status_code == 400
    assert r.json()["detail"] == "Texto vazio."


async def test_tts_unknown_engine_is_400(client: httpx.AsyncClient) -> None:
    """`_canonical` levanta ValueError -> 400 (e não 500)."""
    async with client as c:
        r = await c.post("/tts", json={"text": "olá", "engine": "espeak"})
    assert r.status_code == 400
    assert "espeak" in r.json()["detail"]


async def test_tts_engine_runtime_error_is_503(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Modelo indisponível é 503 (transitório), não 500 — o app pode tentar de
    novo em vez de mostrar erro fatal no meio de um livro."""

    class Broken:
        def synthesize(self, *a, **k):
            raise RuntimeError("modelo indisponível")

    monkeypatch.setattr(api_mod, "get_engine", lambda name: Broken())
    async with client as c:
        r = await c.post("/tts", json={"text": "texto que falha na sintese"})
    assert r.status_code == 503
    assert r.json()["detail"] == "modelo indisponível"


# --------------------------------------------------------------------------- #
# /tts/pregenerate  (POST / GET / DELETE)
# --------------------------------------------------------------------------- #
async def test_pregenerate_post_get_and_fill_cache(
    client: httpx.AsyncClient, fake_engine: FakeEngine
) -> None:
    textos = [f"Paragrafo numero {i} da pre-geracao." for i in range(4)]

    async with client as c:
        started = await c.post("/tts/pregenerate", json={"texts": textos, "engine": "piper"})
        assert started.status_code == 200
        job = started.json()
        assert set(job) == {"id", "status", "done", "total", "error"}
        assert job["total"] == 4
        assert job["status"] == "running"
        assert job["error"] is None

        finished = _wait_for(lambda: pregen.get_job(job["id"]).status == "done")
        assert finished, f"job não terminou: {pregen.get_job(job['id'])}"

        polled = await c.get(f"/tts/pregenerate/{job['id']}")

    assert polled.status_code == 200
    assert polled.json() == {
        "id": job["id"], "status": "done", "done": 4, "total": 4, "error": None,
    }

    # o laço fecha: o que a pré-geração gravou é exatamente o que /tts leria
    for texto in textos:
        key = tts_cache.cache_key("piper", texto, None, "pt", 1.0)
        assert tts_cache.get(key) is not None, f"cache não preenchido para {texto!r}"


async def test_pregenerate_skips_blank_texts(
    client: httpx.AsyncClient, fake_engine: FakeEngine
) -> None:
    """Texto em branco não conta no total — senão a barra de progresso do app
    nunca chegaria a 100%."""
    async with client as c:
        r = await c.post(
            "/tts/pregenerate",
            json={"texts": ["texto de verdade", "", "   ", "\n"]},
        )
    assert r.json()["total"] == 1


async def test_pregenerate_empty_list_is_400(client: httpx.AsyncClient) -> None:
    async with client as c:
        r = await c.post("/tts/pregenerate", json={"texts": []})
    assert r.status_code == 400
    assert r.json()["detail"] == "Lista de textos vazia."


async def test_pregenerate_unknown_job_is_404(client: httpx.AsyncClient) -> None:
    async with client as c:
        r = await c.get("/tts/pregenerate/nao-existe")
    assert r.status_code == 404
    assert r.json()["detail"] == "Job de pré-geração não encontrado."


async def test_pregenerate_delete_cancels(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O DELETE responde `{"cancelled": true}` e o job realmente para.

    A porta (`gate`) torna isso determinístico: o worker fica preso no primeiro
    item até o teste soltá-lo, então o DELETE chega com certeza antes de o job
    terminar."""
    gate = threading.Event()
    monkeypatch.setattr(pregen, "get_engine", lambda name: FakeEngine(gate=gate))

    async with client as c:
        started = await c.post(
            "/tts/pregenerate",
            json={"texts": [f"item {i} do job cancelado" for i in range(6)]},
        )
        job_id = started.json()["id"]

        cancelled = await c.delete(f"/tts/pregenerate/{job_id}")
        assert cancelled.status_code == 200
        assert cancelled.json() == {"cancelled": True}

        gate.set()
        assert _wait_for(lambda: pregen.get_job(job_id).status == "cancelled"), (
            f"job não foi cancelado: {pregen.get_job(job_id)}"
        )

        polled = await c.get(f"/tts/pregenerate/{job_id}")

    body = polled.json()
    assert body["status"] == "cancelled"
    assert body["done"] < body["total"], "cancelou, mas processou tudo mesmo assim"


async def test_pregenerate_delete_unknown_job_is_idempotent(
    client: httpx.AsyncClient,
) -> None:
    """Cancelar um job que não existe não é erro — o app pode mandar DELETE ao
    trocar de capítulo sem saber se ainda há job vivo."""
    async with client as c:
        r = await c.delete("/tts/pregenerate/id-que-nunca-existiu")
    assert r.status_code == 200
    assert r.json() == {"cancelled": True}


async def test_pregenerate_engine_failure_is_recorded_on_the_job(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falha na pré-geração vira status "error" no job, não exceção no POST —
    a pré-geração é background e não pode derrubar a escuta em andamento."""

    class Broken:
        def synthesize(self, *a, **k):
            raise RuntimeError("sem modelo")

    monkeypatch.setattr(pregen, "get_engine", lambda name: Broken())

    async with client as c:
        started = await c.post(
            "/tts/pregenerate", json={"texts": ["um texto que vai falhar"]}
        )
        assert started.status_code == 200
        job_id = started.json()["id"]

        assert _wait_for(lambda: pregen.get_job(job_id).status == "error")
        polled = await c.get(f"/tts/pregenerate/{job_id}")

    body = polled.json()
    assert body["status"] == "error"
    assert body["error"] == "sem modelo"


# --------------------------------------------------------------------------- #
# Superfície de rotas
# --------------------------------------------------------------------------- #
async def test_route_surface_is_the_seven_known_routes() -> None:
    """Trava a superfície: se uma rota nova aparecer sem teste, isto quebra."""
    from main import app

    routes = {
        (r.path, method)
        for r in app.routes
        for method in getattr(r, "methods", set())
        if method not in ("HEAD", "OPTIONS")
    }
    assert routes >= {
        ("/health", "GET"),
        ("/extract", "POST"),
        ("/tts/engines", "GET"),
        ("/tts", "POST"),
        ("/tts/pregenerate", "POST"),
        ("/tts/pregenerate/{job_id}", "GET"),
        ("/tts/pregenerate/{job_id}", "DELETE"),
    }
    app_routes = {r for r in routes if not r[0].startswith("/openapi")}
    app_routes = {r for r in app_routes if r[0] not in ("/docs", "/redoc", "/docs/oauth2-redirect")}
    assert len(app_routes) == 7, f"superfície de rotas mudou: {sorted(app_routes)}"
