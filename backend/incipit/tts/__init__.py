"""Registro de engines de TTS. Instâncias são cacheadas (modelos carregam uma vez)."""

from __future__ import annotations

from functools import lru_cache

from .base import TTSEngine

AVAILABLE_ENGINES = ["piper", "xtts"]


@lru_cache(maxsize=None)
def get_engine(name: str | None) -> TTSEngine:
    key = (name or "piper").lower()
    if key == "piper":
        from .piper import PiperEngine

        return PiperEngine()
    if key in ("xtts", "coqui", "xtts_v2"):
        from .xtts import XTTSEngine

        return XTTSEngine()
    raise ValueError(f"Engine de TTS desconhecido: {name!r} — use 'piper' ou 'xtts'")
