"""Interface comum dos engines de TTS."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TTSEngine(ABC):
    """Contrato de um engine de síntese de voz.

    `synthesize` recebe texto e devolve áudio WAV (PCM 16-bit mono) como bytes.
    Engines podem carregar modelos preguiçosamente na primeira chamada.
    """

    name: str

    @abstractmethod
    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        language: str = "pt",
        speed: float = 1.0,
    ) -> bytes:
        ...
