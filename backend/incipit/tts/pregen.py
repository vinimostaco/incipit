"""Pré-geração de áudio em background.

Sintetiza antecipadamente um conjunto de parágrafos (capítulo ou livro) e
preenche o cache em disco, para que a escuta depois seja cache hit instantâneo.
Pensado para o XTTS, que em CPU não acompanha a escuta em tempo real.

Cada job roda em sua própria thread; a síntese é serializada por um lock do
*mesmo* engine, então a escuta JIT do usuário intercala entre os itens — e um
engine diferente (ex.: Piper) nunca espera atrás da pré-geração do XTTS.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass

from . import cache as tts_cache
from . import get_engine, synth_lock_for


@dataclass
class PregenJob:
    id: str
    engine: str
    voice: str | None
    total: int
    done: int = 0
    status: str = "running"  # running | done | cancelled | error
    error: str | None = None


_jobs: dict[str, PregenJob] = {}
_cancel: set[str] = set()
_lock = threading.Lock()


def start_job(
    engine: str,
    voice: str | None,
    texts: list[str],
    language: str,
    speed: float,
) -> PregenJob:
    # (texto_limpo, cache_key) — mesma chave usada pelo endpoint /tts
    items: list[tuple[str, str]] = []
    for t in texts:
        s = (t or "").strip()
        if s:
            items.append((s, tts_cache.cache_key(engine, s, voice, language, speed)))

    job = PregenJob(id=uuid.uuid4().hex, engine=engine, voice=voice, total=len(items))
    with _lock:
        _jobs[job.id] = job

    thread = threading.Thread(
        target=_run, args=(job, items, language, speed), daemon=True
    )
    thread.start()
    return job


def get_job(job_id: str) -> PregenJob | None:
    return _jobs.get(job_id)


def cancel_job(job_id: str) -> None:
    _cancel.add(job_id)


def _run(job: PregenJob, items: list[tuple[str, str]], language: str, speed: float) -> None:
    try:
        engine = get_engine(job.engine)
    except Exception as e:
        job.status, job.error = "error", str(e)
        return

    lock = synth_lock_for(job.engine)
    for text, key in items:
        if job.id in _cancel:
            job.status = "cancelled"
            break
        if tts_cache.get(key) is None:
            try:
                with lock:
                    audio = engine.synthesize(
                        text, voice=job.voice, language=language, speed=speed
                    )
                tts_cache.put(key, audio)
            except Exception as e:
                job.status, job.error = "error", str(e)
                _cancel.discard(job.id)
                return
        job.done += 1
    else:
        job.status = "done"

    _cancel.discard(job.id)
