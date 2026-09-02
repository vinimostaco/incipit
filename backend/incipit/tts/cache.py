"""Cache de áudio em disco, indexado por (engine, voz, idioma, velocidade, texto).

Sustenta a estratégia de cache progressivo: um trecho já sintetizado nunca é
gerado de novo, e a pré-geração antecipada (XTTS) só preenche este cache.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import AUDIO_CACHE_DIR


def cache_key(engine: str, text: str, voice: str | None, language: str, speed: float) -> str:
    h = hashlib.sha256()
    h.update(f"{engine}\x00{voice}\x00{language}\x00{speed:.3f}\x00{text}".encode("utf-8"))
    return h.hexdigest()


def cache_path(key: str) -> Path:
    return AUDIO_CACHE_DIR / f"{key}.wav"


def get(key: str) -> bytes | None:
    p = cache_path(key)
    return p.read_bytes() if p.is_file() else None


def put(key: str, data: bytes) -> Path:
    p = cache_path(key)
    # O diretório é criado aqui, e não no import de `config`: gravar é o que
    # justifica o efeito colateral. `exist_ok` cobre a concorrência entre a
    # escuta JIT e a thread de pré-geração gravando ao mesmo tempo.
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".wav.part")
    tmp.write_bytes(data)
    tmp.replace(p)
    return p
