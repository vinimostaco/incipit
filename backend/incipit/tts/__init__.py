"""Registro de engines de TTS. Instâncias são cacheadas (modelos carregam uma vez)."""

from __future__ import annotations

import threading
from functools import lru_cache

from .base import TTSEngine

AVAILABLE_ENGINES = ["piper", "xtts"]


def _canonical(name: str | None) -> str:
    key = (name or "piper").lower()
    if key == "piper":
        return "piper"
    if key in ("xtts", "coqui", "xtts_v2"):
        return "xtts"
    raise ValueError(f"Engine de TTS desconhecido: {name!r} — use 'piper' ou 'xtts'")


# Um lock por engine, não um global. O objetivo é só evitar dois forwards do
# *mesmo* modelo em paralelo; um cadeado único faria o Piper (rápido) esperar
# atrás do XTTS (lento, pesado em CPU) — travando a troca de voz e a escuta JIT
# enquanto a pré-geração do XTTS roda em background.
_engine_locks: dict[str, threading.Lock] = {}
_engine_locks_guard = threading.Lock()


def synth_lock_for(name: str | None) -> threading.Lock:
    key = _canonical(name)
    with _engine_locks_guard:
        lock = _engine_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _engine_locks[key] = lock
        return lock


@lru_cache(maxsize=None)
def get_engine(name: str | None) -> TTSEngine:
    key = _canonical(name)
    if key == "piper":
        from .piper import PiperEngine

        return PiperEngine()
    from .xtts import XTTSEngine

    return XTTSEngine()
