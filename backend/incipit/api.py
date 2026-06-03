"""Rotas HTTP do backend: extração de texto e síntese de voz."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from . import extract as extract_mod
from .models import Book, ExtractRequest, TTSRequest
from .tts import AVAILABLE_ENGINES, get_engine
from .tts import cache as tts_cache

router = APIRouter()


@router.post("/extract", response_model=Book)
def extract_endpoint(req: ExtractRequest) -> Book:
    try:
        return extract_mod.extract(req.path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover - rede de segurança
        raise HTTPException(status_code=500, detail=f"Falha ao extrair: {e}")


@router.get("/tts/engines")
def tts_engines() -> dict:
    return {"engines": AVAILABLE_ENGINES}


@router.post("/tts")
def tts_endpoint(req: TTSRequest) -> Response:
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto vazio.")

    key = tts_cache.cache_key(req.engine, text, req.voice, req.language, req.speed)
    audio = tts_cache.get(key)
    cached = audio is not None

    if audio is None:
        try:
            engine = get_engine(req.engine)
            audio = engine.synthesize(
                text, voice=req.voice, language=req.language, speed=req.speed
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:  # pragma: no cover - rede de segurança
            raise HTTPException(status_code=500, detail=f"Falha no TTS: {e}")
        tts_cache.put(key, audio)

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"X-Cache": "hit" if cached else "miss", "X-Cache-Key": key},
    )
