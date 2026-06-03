// Hook de reprodução: percorre a sequência de parágrafos, sintetiza áudio sob
// demanda, faz prefetch dos próximos (cache progressivo) e auto-avança.
import { useCallback, useEffect, useRef, useState } from "react";

import { synthesize } from "./api";
import type { FlatPara } from "./types";

const PREFETCH_AHEAD = 2;

interface Opts {
  paras: FlatPara[];
  engine: string;
  voice: string | null;
  startIndex: number;
  onIndexChange?: (i: number) => void;
}

export function usePlayer({ paras, engine, voice, startIndex, onIndexChange }: Opts) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  if (audioRef.current === null) audioRef.current = new Audio();

  const [index, setIndex] = useState(startIndex);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [progress, setProgress] = useState(0); // 0..1 dentro do parágrafo atual
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const indexRef = useRef(index);
  indexRef.current = index;
  const speedRef = useRef(speed);
  speedRef.current = speed;

  // globalIndex -> objectURL do áudio já sintetizado
  const cacheRef = useRef<Map<number, string>>(new Map());
  const inflightRef = useRef<Map<number, Promise<string>>>(new Map());

  const getAudioUrl = useCallback(
    async (i: number): Promise<string> => {
      const cached = cacheRef.current.get(i);
      if (cached) return cached;
      const pending = inflightRef.current.get(i);
      if (pending) return pending;

      const p = synthesize(paras[i].text, engine, voice).then((blob) => {
        const url = URL.createObjectURL(blob);
        cacheRef.current.set(i, url);
        inflightRef.current.delete(i);
        return url;
      });
      inflightRef.current.set(i, p);
      return p;
    },
    [paras, engine, voice],
  );

  const prefetch = useCallback(
    (from: number) => {
      for (let k = 1; k <= PREFETCH_AHEAD; k++) {
        const j = from + k;
        if (j < paras.length && !cacheRef.current.has(j) && !inflightRef.current.has(j)) {
          getAudioUrl(j).catch(() => {});
        }
      }
    },
    [paras.length, getAudioUrl],
  );

  const load = useCallback(
    async (i: number, autoplay: boolean) => {
      if (i < 0 || i >= paras.length) return;
      setIndex(i);
      onIndexChange?.(i);
      setProgress(0);
      setError(null);
      setLoading(true);
      try {
        const url = await getAudioUrl(i);
        const audio = audioRef.current!;
        audio.src = url;
        audio.playbackRate = speedRef.current;
        if (autoplay) await audio.play();
        prefetch(i);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Falha ao gerar áudio");
        setIsPlaying(false);
      } finally {
        setLoading(false);
      }
    },
    [paras, getAudioUrl, prefetch, onIndexChange],
  );

  const goNext = useCallback(
    (autoplay: boolean) => {
      const i = indexRef.current + 1;
      if (i < paras.length) load(i, autoplay);
      else setIsPlaying(false);
    },
    [paras.length, load],
  );

  const goPrev = useCallback(() => {
    load(Math.max(0, indexRef.current - 1), true);
  }, [load]);

  const jumpTo = useCallback((i: number) => load(i, true), [load]);

  const togglePlay = useCallback(async () => {
    const audio = audioRef.current!;
    if (audio.paused) {
      if (!audio.src) await load(indexRef.current, true);
      else await audio.play().catch(() => {});
    } else {
      audio.pause();
    }
  }, [load]);

  const seek = useCallback((fraction: number) => {
    const audio = audioRef.current!;
    if (audio.duration && isFinite(audio.duration)) {
      audio.currentTime = Math.max(0, Math.min(1, fraction)) * audio.duration;
    }
  }, []);

  const changeSpeed = useCallback((s: number) => {
    setSpeed(s);
    speedRef.current = s;
    if (audioRef.current) audioRef.current.playbackRate = s;
  }, []);

  // Liga os eventos do <audio> ao estado.
  useEffect(() => {
    const audio = audioRef.current!;
    const onTime = () => setProgress(audio.duration ? audio.currentTime / audio.duration : 0);
    const onEnded = () => goNext(true);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);
    return () => {
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
    };
  }, [goNext]);

  // Troca de livro/engine/voz invalida o cache de áudio.
  useEffect(() => {
    const cache = cacheRef.current;
    const inflight = inflightRef.current;
    return () => {
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audio.removeAttribute("src");
        audio.load();
      }
      for (const url of cache.values()) URL.revokeObjectURL(url);
      cache.clear();
      inflight.clear();
    };
  }, [paras, engine, voice]);

  return {
    index,
    isPlaying,
    speed,
    progress,
    loading,
    error,
    togglePlay,
    goNext,
    goPrev,
    jumpTo,
    seek,
    changeSpeed,
  };
}
