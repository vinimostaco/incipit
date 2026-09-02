"""Engine Piper — rápido em CPU (10-30x tempo real), ideal para cache progressivo
JIT e escuta imediata. Vozes PT-BR baixadas sob demanda do catálogo oficial."""

from __future__ import annotations

import io
import threading
import wave

from ..config import MODELS_DIR
from .base import TTSEngine

# Vozes PT-BR do catálogo rhasspy/piper-voices.
PT_VOICES = [
    "pt_BR-faber-medium",
    "pt_BR-edresson-low",
    "pt_BR-cadu-medium",
    "pt_BR-jeff-medium",
]
DEFAULT_VOICE = "pt_BR-faber-medium"


class PiperEngine(TTSEngine):
    name = "piper"

    def __init__(self) -> None:
        self._voices: dict[str, object] = {}
        self._lock = threading.Lock()

    def _resolve_voice(self, voice: str | None) -> str:
        if not voice:
            return DEFAULT_VOICE
        if voice in PT_VOICES:
            return voice
        # aceita nome curto, ex.: "faber" -> "pt_BR-faber-medium"
        for v in PT_VOICES:
            if voice in v:
                return v
        return DEFAULT_VOICE

    def _load(self, voice: str):
        from piper import PiperVoice
        from piper.download_voices import download_voice

        with self._lock:
            if voice not in self._voices:
                model = MODELS_DIR / f"{voice}.onnx"
                if not model.is_file():
                    # `download_voice` grava direto em MODELS_DIR e não cria o
                    # diretório; ele é criado aqui, na primeira voz carregada,
                    # em vez de no import de `config`.
                    MODELS_DIR.mkdir(parents=True, exist_ok=True)
                    download_voice(voice, MODELS_DIR)
                self._voices[voice] = PiperVoice.load(str(model), f"{model}.json")
            return self._voices[voice]

    def synthesize(self, text, *, voice=None, language="pt", speed=1.0) -> bytes:
        from piper import SynthesisConfig

        v = self._load(self._resolve_voice(voice))
        # length_scale > 1 deixa mais lento; usamos o inverso da velocidade pedida.
        length_scale = 1.0 / speed if speed and speed > 0 else 1.0
        cfg = SynthesisConfig(length_scale=length_scale)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            v.synthesize_wav(text, wf, syn_config=cfg)
        return buf.getvalue()
