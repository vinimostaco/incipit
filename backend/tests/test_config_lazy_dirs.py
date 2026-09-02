"""Importar `incipit` não pode escrever no disco.

`config.py` fazia `mkdir` no import: bastava importar qualquer módulo do pacote
para o processo criar `~/.local/share/incipit/{models,tts-cache}` — e, se o
caminho não fosse gravável, o import explodia antes de qualquer rota subir.

Num app desktop isso é pior do que parece: o sidecar é um binário PyInstaller
lançado pelo Tauri, e um import que levanta exceção mata o backend na
inicialização. O usuário vê "abrindo…" para sempre, sem erro visível, porque
quem morreu foi o outro processo. Criar diretório é efeito colateral e pertence
a quem realmente vai gravar: `cache.put` e `piper._load`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent


def _run_import(data_dir: str, snippet: str = "") -> subprocess.CompletedProcess:
    # O dedent é aplicado ao template ANTES da substituição: um `snippet` de
    # várias linhas mudaria o prefixo comum e quebraria a indentação.
    code = "\n".join(
        ["import incipit.config, incipit.tts.cache", textwrap.dedent(snippet).strip(),
         'print("IMPORT_OK")']
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND,
        # HOME entra porque o *default* de `os.environ.get` em config.py é
        # `Path.home() / ...`, que o Python avalia sempre — mesmo quando
        # INCIPIT_DATA_DIR está definido e o default é descartado.
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": os.environ.get("HOME", "/tmp"),
            "INCIPIT_DATA_DIR": data_dir,
        },
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_import_does_not_fail_on_unwritable_data_dir() -> None:
    """O critério literal do brief: um INCIPIT_DATA_DIR impossível de criar não
    pode impedir o pacote de ser importado."""
    result = _run_import("/proc/nao-gravavel")
    assert result.returncode == 0, (
        f"import falhou com INCIPIT_DATA_DIR inválido:\n{result.stderr}"
    )
    assert "IMPORT_OK" in result.stdout


def test_import_creates_no_directories(tmp_path: Path) -> None:
    """Contrapositivo do teste acima: mesmo com um caminho perfeitamente
    gravável, o import não deve criar nada. Se criasse, o teste de cima estaria
    passando por acidente (ex.: exceção engolida)."""
    target = tmp_path / "dados-do-incipit"
    result = _run_import(str(target))

    assert result.returncode == 0, result.stderr
    assert not target.exists(), (
        f"o import criou {target} — o mkdir deveria ser sob demanda"
    )


def test_config_still_exposes_the_expected_paths(tmp_path: Path) -> None:
    """A correção é só sobre o efeito colateral: os caminhos continuam os
    mesmos, derivados de INCIPIT_DATA_DIR."""
    target = tmp_path / "dados"
    result = _run_import(
        str(target),
        snippet=textwrap.dedent(
            """
            from incipit.config import DATA_DIR, MODELS_DIR, AUDIO_CACHE_DIR
            assert MODELS_DIR == DATA_DIR / "models", MODELS_DIR
            assert AUDIO_CACHE_DIR == DATA_DIR / "tts-cache", AUDIO_CACHE_DIR
            """
        ),
    )
    assert result.returncode == 0, result.stderr


def test_cache_put_creates_the_cache_dir_on_demand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from incipit.tts import cache as tts_cache

    fresh = tmp_path / "ainda" / "nao" / "existe"
    monkeypatch.setattr(tts_cache, "AUDIO_CACHE_DIR", fresh)
    assert not fresh.exists()

    key = tts_cache.cache_key("piper", "texto", None, "pt", 1.0)
    path = tts_cache.put(key, b"RIFF....")

    assert fresh.is_dir(), "cache.put não criou o diretório de cache"
    assert path.read_bytes() == b"RIFF...."
    assert tts_cache.get(key) == b"RIFF...."


def test_cache_get_on_missing_dir_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ler de um cache que ainda não existe é miss, não exceção."""
    from incipit.tts import cache as tts_cache

    monkeypatch.setattr(tts_cache, "AUDIO_CACHE_DIR", tmp_path / "vazio")
    assert tts_cache.get(tts_cache.cache_key("piper", "x", None, "pt", 1.0)) is None


def test_piper_load_creates_models_dir_before_downloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_load` precisa criar MODELS_DIR *antes* de chamar `download_voice` —
    o piper grava direto nesse caminho e não o cria sozinho."""
    import types

    from incipit.tts import piper as piper_mod

    fresh = tmp_path / "models-sob-demanda"
    monkeypatch.setattr(piper_mod, "MODELS_DIR", fresh)

    seen: dict[str, object] = {}

    def fake_download_voice(voice, dest):
        seen["dir_existia"] = Path(dest).is_dir()
        seen["voice"] = voice
        Path(dest, f"{voice}.onnx").write_bytes(b"fake-model")

    class FakePiperVoice:
        @staticmethod
        def load(model_path, config_path):
            seen["loaded"] = model_path
            return "voz-carregada"

    fake_piper = types.ModuleType("piper")
    fake_piper.PiperVoice = FakePiperVoice
    fake_downloads = types.ModuleType("piper.download_voices")
    fake_downloads.download_voice = fake_download_voice

    monkeypatch.setitem(sys.modules, "piper", fake_piper)
    monkeypatch.setitem(sys.modules, "piper.download_voices", fake_downloads)

    engine = piper_mod.PiperEngine()
    assert engine._load("pt_BR-faber-medium") == "voz-carregada"

    assert seen["dir_existia"] is True, (
        "download_voice foi chamado antes de MODELS_DIR existir"
    )
    assert fresh.is_dir()
    assert seen["voice"] == "pt_BR-faber-medium"
