"""Caminhos de dados do incipit (modelos de voz e cache de áudio).

Tudo fica sob INCIPIT_DATA_DIR (padrão: ~/.local/share/incipit), fora do
repositório, para não versionar modelos pesados nem áudio gerado.
"""

from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(
    os.environ.get("INCIPIT_DATA_DIR", Path.home() / ".local" / "share" / "incipit")
).expanduser()

MODELS_DIR = DATA_DIR / "models"
AUDIO_CACHE_DIR = DATA_DIR / "tts-cache"

for _d in (MODELS_DIR, AUDIO_CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)
