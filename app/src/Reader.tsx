// Tela de leitura: lista de parágrafos por capítulo + barra de player.
import type * as React from "react";
import { useEffect, useRef, useState } from "react";

import { pregenCancel, pregenStatus, pregenerate, type PregenStatus } from "./api";
import { usePlayer } from "./usePlayer";
import type { FlatPara, LibraryEntry } from "./types";

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

  // Mantém o parágrafo atual visível.
  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${player.index}"]`);
    el?.scrollIntoView({ block: "center", behavior: "smooth" });
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

  function changeEngine(e: string) {
    const v = e === "piper" ? voice ?? PIPER_VOICES[0].id : null;
    setEngine(e);
    setVoice(v);
    onSettings(e, v);
  }

  function changeVoice(v: string) {
    setVoice(v);
    onSettings(engine, v);
  }

  function onSeekClick(ev: React.MouseEvent<HTMLDivElement>) {
    const rect = ev.currentTarget.getBoundingClientRect();
    player.seek((ev.clientX - rect.left) / rect.width);
  }

  const current = paras[player.index];

  return (
    <div className="reader">
      <header className="reader-head">
        <div className="reader-title">
          <h1>{entry.title}</h1>
          {entry.author && <span className="author">{entry.author}</span>}
        </div>
        <div className="settings">
          <select value={engine} onChange={(e) => changeEngine(e.target.value)} title="Motor de voz">
            {ENGINES.map((e) => (
              <option key={e.id} value={e.id}>
                {e.label}
              </option>
            ))}
          </select>
          {engine === "piper" && (
            <select value={voice ?? ""} onChange={(e) => changeVoice(e.target.value)} title="Voz">
              {PIPER_VOICES.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          )}
          <div className="pregen-actions" title="Gerar o áudio antecipadamente para escuta sem pausas (essencial no XTTS)">
            <span>Pré-gerar:</span>
            <button onClick={() => startPregen("chapter")} disabled={pregenRunning}>
              Capítulo
            </button>
            <button onClick={() => startPregen("book")} disabled={pregenRunning}>
              Livro
            </button>
          </div>
        </div>
      </header>

      {(pregen || pregenErr) && (
        <div className="pregen-bar">
          {pregenErr && <span className="pregen-err">{pregenErr}</span>}
          {pregenRunning && (
            <>
              <span className="pregen-label">
                Pré-gerando voz… {pregen!.done}/{pregen!.total}
              </span>
              <div className="pregen-track">
                <div
                  className="pregen-fill"
                  style={{ width: `${pregen!.total ? (pregen!.done / pregen!.total) * 100 : 0}%` }}
                />
              </div>
              <button onClick={cancelPregen}>Cancelar</button>
            </>
          )}
          {pregen?.status === "done" && (
            <span className="pregen-done">✓ Áudio pronto — escuta sem pausas</span>
          )}
          {pregen?.status === "cancelled" && <span>Pré-geração cancelada.</span>}
          {pregen?.status === "error" && (
            <span className="pregen-err">Erro na pré-geração: {pregen.error}</span>
          )}
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

      <div className="player">
        <div className="seek" onClick={onSeekClick} title="Avançar/retroceder no parágrafo">
          <div className="seek-fill" style={{ width: `${player.progress * 100}%` }} />
        </div>
        <div className="controls">
          <button onClick={player.goPrev} title="Parágrafo anterior">
            ⏮
          </button>
          <button className="play" onClick={player.togglePlay} title="Reproduzir/pausar">
            {player.isPlaying ? "⏸" : "▶"}
          </button>
          <button onClick={() => player.goNext(true)} title="Próximo parágrafo">
            ⏭
          </button>

          <span className="pos">
            {paras.length ? player.index + 1 : 0} / {paras.length}
          </span>

          <label className="speed">
            Velocidade
            <select value={player.speed} onChange={(e) => player.changeSpeed(Number(e.target.value))}>
              {SPEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}×
                </option>
              ))}
            </select>
          </label>

          <span className="status">
            {player.loading ? "gerando voz…" : current?.chapterTitle ?? ""}
          </span>
        </div>
        {player.error && <div className="player-error">{player.error}</div>}
      </div>
    </div>
  );
}
