// Tela de leitura: lista de parágrafos por capítulo + barra de player.
import type * as React from "react";
import { useEffect, useRef, useState } from "react";

import { pregenCancel, pregenStatus, pregenerate, type PregenStatus } from "./api";
import { usePlayer } from "./usePlayer";
import type { FlatPara, LibraryEntry } from "./types";
import { Notice, Spinner, prefersReducedMotion } from "./ui";

const ENGINES = [
  { id: "piper", label: "Piper — rápido (recomendado)" },
  { id: "xtts", label: "XTTS — alta qualidade (lento)" },
];

const PIPER_VOICES = [
  { id: "pt_BR-faber-medium", label: "Faber" },
  { id: "pt_BR-edresson-low", label: "Edresson" },
  { id: "pt_BR-cadu-medium", label: "Cadu" },
  { id: "pt_BR-jeff-medium", label: "Jeff" },
];

const SPEEDS = [0.75, 1, 1.25, 1.5, 1.75, 2];

// Ícones em SVG: não dependem de o sistema ter a fonte com os glifos ⏮/⏸/▶.
const IconPrev = () => (
  <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="currentColor">
    <path d="M4 2h2v12H4zM14 2v12L6.5 8z" />
  </svg>
);
const IconNext = () => (
  <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="currentColor">
    <path d="M10 2h2v12h-2zM2 2v12L9.5 8z" />
  </svg>
);
const IconPlay = () => (
  <svg viewBox="0 0 16 16" width="20" height="20" aria-hidden="true" fill="currentColor">
    <path d="M3.5 1.8v12.4L14 8z" />
  </svg>
);
const IconPause = () => (
  <svg viewBox="0 0 16 16" width="20" height="20" aria-hidden="true" fill="currentColor">
    <path d="M3.5 2h3.2v12H3.5zM9.3 2h3.2v12H9.3z" />
  </svg>
);

interface Props {
  entry: LibraryEntry;
  paras: FlatPara[];
  onProgress: (i: number) => void;
  onSettings: (engine: string, voice: string | null) => void;
}

export function Reader({ entry, paras, onProgress, onSettings }: Props) {
  const [engine, setEngine] = useState(entry.engine);
  const [voice, setVoice] = useState<string | null>(entry.voice);

  const player = usePlayer({
    paras,
    engine,
    voice,
    startIndex: entry.progressIndex,
    onIndexChange: onProgress,
  });

  const [pregen, setPregen] = useState<PregenStatus | null>(null);
  const [pregenErr, setPregenErr] = useState<string | null>(null);

  const listRef = useRef<HTMLDivElement>(null);

  // Mantém o parágrafo atual visível — sem rolagem animada para quem pediu
  // menos movimento.
  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${player.index}"]`);
    el?.scrollIntoView({ block: "center", behavior: prefersReducedMotion() ? "auto" : "smooth" });
  }, [player.index]);

  // Acompanha o progresso de um job de pré-geração.
  useEffect(() => {
    if (!pregen || pregen.status !== "running") return;
    const id = pregen.id;
    const t = setInterval(async () => {
      try {
        setPregen(await pregenStatus(id));
      } catch {
        /* mantém o último estado em caso de falha transitória */
      }
    }, 1000);
    return () => clearInterval(t);
  }, [pregen?.id, pregen?.status]);

  // Some com a barra alguns segundos depois de concluir.
  useEffect(() => {
    if (pregen?.status !== "done") return;
    const t = setTimeout(() => setPregen(null), 5000);
    return () => clearTimeout(t);
  }, [pregen?.status]);

  async function startPregen(scope: "chapter" | "book") {
    setPregenErr(null);
    const texts =
      scope === "book"
        ? paras.map((p) => p.text)
        : paras
            .filter((p) => p.chapterIndex === paras[player.index]?.chapterIndex)
            .map((p) => p.text);
    try {
      setPregen(await pregenerate(texts, engine, voice));
    } catch (e) {
      setPregenErr(e instanceof Error ? e.message : "Falha ao iniciar a pré-geração");
    }
  }

  function cancelPregen() {
    if (pregen) pregenCancel(pregen.id);
  }

  const pregenRunning = pregen?.status === "running";

  // A pré-geração é específica de um engine/voz; ao trocar, cancela a que roda
  // (não serve mais) e limpa a barra de progresso.
  function stopPregen() {
    if (pregen?.status === "running") pregenCancel(pregen.id);
    setPregen(null);
    setPregenErr(null);
  }

  function changeEngine(e: string) {
    const v = e === "piper" ? voice ?? PIPER_VOICES[0].id : null;
    stopPregen();
    setEngine(e);
    setVoice(v);
    onSettings(e, v);
  }

  function changeVoice(v: string) {
    stopPregen();
    setVoice(v);
    onSettings(engine, v);
  }

  function onSeekClick(ev: React.MouseEvent<HTMLDivElement>) {
    const rect = ev.currentTarget.getBoundingClientRect();
    player.seek((ev.clientX - rect.left) / rect.width);
  }

  // A barra de posição também responde ao teclado (usa o mesmo player.seek).
  function onSeekKey(ev: React.KeyboardEvent<HTMLDivElement>) {
    const step = ev.key === "ArrowLeft" ? -0.05 : ev.key === "ArrowRight" ? 0.05 : 0;
    if (!step) return;
    ev.preventDefault();
    player.seek(Math.min(1, Math.max(0, player.progress + step)));
  }

  const current = paras[player.index];
  const pregenPct = pregen?.total ? Math.round((pregen.done / pregen.total) * 100) : 0;

  return (
    <div className="reader">
      <header className="reader-head">
        <div className="reader-title">
          <h1>{entry.title}</h1>
          {entry.author && <span className="author">{entry.author}</span>}
        </div>
        <div className="settings">
          <label className="field">
            <span className="field-label">Motor</span>
            <select value={engine} onChange={(e) => changeEngine(e.target.value)}>
              {ENGINES.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.label}
                </option>
              ))}
            </select>
          </label>
          {engine === "piper" && (
            <label className="field">
              <span className="field-label">Voz</span>
              <select value={voice ?? ""} onChange={(e) => changeVoice(e.target.value)}>
                {PIPER_VOICES.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div
            className="pregen-actions"
            title="Gerar o áudio antecipadamente para escuta sem pausas (essencial no XTTS)"
          >
            <span className="field-label">Pré-gerar</span>
            <div className="pregen-buttons">
              <button className="btn-ghost" onClick={() => startPregen("chapter")} disabled={pregenRunning}>
                Capítulo
              </button>
              <button className="btn-ghost" onClick={() => startPregen("book")} disabled={pregenRunning}>
                Livro
              </button>
            </div>
          </div>
        </div>
      </header>

      {pregenErr && (
        <Notice kind="error" title="Falha na pré-geração" onDismiss={() => setPregenErr(null)}>
          {pregenErr}
        </Notice>
      )}

      {pregen && (
        <div className="pregen-bar" role="status">
          {pregenRunning && (
            <>
              <span className="pregen-label">
                Pré-gerando voz — {pregen.done}/{pregen.total} ({pregenPct}%)
              </span>
              <div
                className="pregen-track"
                role="progressbar"
                aria-label="Progresso da pré-geração"
                aria-valuenow={pregenPct}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div className="pregen-fill" style={{ width: `${pregenPct}%` }} />
              </div>
              <button className="btn-ghost" onClick={cancelPregen}>
                Cancelar
              </button>
            </>
          )}
          {pregen.status === "done" && (
            <span className="pregen-done">✓ Áudio pronto — escuta sem pausas</span>
          )}
          {pregen.status === "cancelled" && <span>Pré-geração cancelada.</span>}
          {pregen.status === "error" && <span>Erro na pré-geração: {pregen.error}</span>}
        </div>
      )}

      <div className="paras" ref={listRef}>
        {paras.length === 0 && <p className="empty">Nenhum texto extraído deste arquivo.</p>}
        {paras.map((p, i) => {
          const newChapter = i === 0 || paras[i - 1].chapterIndex !== p.chapterIndex;
          return (
            <div key={p.globalIndex}>
              {newChapter && p.chapterTitle && <h2 className="chapter">{p.chapterTitle}</h2>}
              <p
                data-idx={i}
                className={`para${i === player.index ? " current" : ""}`}
                onClick={() => player.jumpTo(i)}
              >
                {p.text}
              </p>
            </div>
          );
        })}
      </div>

      <div className="player" data-testid="player" data-loading={player.loading ? "true" : "false"}>
        <div
          className="seek"
          role="slider"
          tabIndex={0}
          aria-label="Posição no parágrafo"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(player.progress * 100)}
          onClick={onSeekClick}
          onKeyDown={onSeekKey}
          title="Avançar/retroceder no parágrafo"
        >
          <div className="seek-fill" style={{ width: `${player.progress * 100}%` }} />
        </div>

        <div className="controls">
          <button onClick={player.goPrev} title="Parágrafo anterior" aria-label="Parágrafo anterior">
            <IconPrev />
          </button>
          <button
            className="play"
            onClick={player.togglePlay}
            title={player.isPlaying ? "Pausar" : "Reproduzir"}
            aria-label={player.isPlaying ? "Pausar" : "Reproduzir"}
          >
            {player.isPlaying ? <IconPause /> : <IconPlay />}
            {player.loading && <span className="play-ring" aria-hidden="true" />}
          </button>
          <button onClick={() => player.goNext(true)} title="Próximo parágrafo" aria-label="Próximo parágrafo">
            <IconNext />
          </button>

          <span className="pos">
            {paras.length ? player.index + 1 : 0} / {paras.length}
          </span>

          <label className="speed">
            <span className="field-label">Velocidade</span>
            <select
              value={player.speed}
              aria-label="Velocidade de leitura"
              onChange={(e) => player.changeSpeed(Number(e.target.value))}
            >
              {SPEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}×
                </option>
              ))}
            </select>
          </label>

          {/* "gerando" e "tocando" ocupam slots distintos: o capítulo nunca é
              substituído pelo aviso de carregamento. */}
          <div className="player-now">
            {player.loading && (
              <span className="player-loading" data-testid="player-loading" role="status">
                <Spinner size={14} />
                gerando voz…
              </span>
            )}
            <span className="player-chapter" data-testid="player-chapter">
              {current?.chapterTitle ?? ""}
            </span>
          </div>
        </div>

        {player.error && (
          <Notice kind="error" title="Falha ao gerar o áudio">
            {player.error}
          </Notice>
        )}
      </div>
    </div>
  );
}
