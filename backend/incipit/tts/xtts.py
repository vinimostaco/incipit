"""Engine XTTS v2 (Coqui) — voz quase humana, mas lento em CPU (~0,3-0,5x tempo
real nesta máquina sem GPU). Pensado para pré-geração antecipada, não JIT.

Dependência pesada (PyTorch) e opcional: instale com `uv sync --extra xtts`.
O import é preguiçoso para o backend subir mesmo sem o XTTS instalado.
"""

from __future__ import annotations

import io
import os
import threading
import wave

from .base import TTSEngine

# Falante embutido do XTTS v2 (voz PT-BR agradável). Pode receber outro via `voice`.
DEFAULT_SPEAKER = "Ana Florence"


class XTTSEngine(TTSEngine):
    name = "xtts"

    def __init__(self) -> None:
        self._tts = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._tts is None:
                try:
                    from TTS.api import TTS
                except ImportError as e:
                    raise RuntimeError(
                        "Engine XTTS não está instalado. No diretório backend rode: "
                        "uv sync --extra xtts"
                    ) from e
                os.environ.setdefault("COQUI_TOS_AGREED", "1")
                self._tts = TTS(
                    "tts_models/multilingual/multi-dataset/xtts_v2",
                    progress_bar=False,
                )
            return self._tts

    def synthesize(self, text, *, voice=None, language="pt", speed=1.0) -> bytes:
        import numpy as np

        tts = self._load()
        wav = tts.tts(
            text=text,
            speaker=voice or DEFAULT_SPEAKER,
            language=language or "pt",
            speed=speed or 1.0,
        )

        arr = np.clip(np.asarray(wav, dtype="float32"), -1.0, 1.0)
        pcm = (arr * 32767.0).astype("<i2")
        sr = int(getattr(tts.synthesizer, "output_sample_rate", 24000) or 24000)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue()
