import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";

import { checkHealth, extractBook } from "./api";
import { Reader } from "./Reader";
import { loadLibrary, removeEntry, renameEntry, saveLibrary, upsertEntry } from "./storage";
import type { Book, FlatPara, LibraryEntry } from "./types";
import { ExtractSkeleton, Notice } from "./ui";
import logoUrl from "./assets/logo.svg";
import "./App.css";

const DEFAULT_VOICE = "pt_BR-faber-medium";

// Estado do backend em texto — nunca só na cor do ponto (critério 5).
const BACKEND_STATE = {
  checking: { className: "checking", label: "verificando backend…" },
  up: { className: "up", label: "backend online" },
  down: { className: "down", label: "backend offline" },
} as const;

function flatten(book: Book): FlatPara[] {
  const out: FlatPara[] = [];
  for (const ch of book.chapters) {
    for (const p of ch.paragraphs) {
      out.push({
        globalIndex: out.length,
        chapterIndex: ch.index,
        chapterTitle: ch.title,
        text: p.text,
      });
    }
  }
  return out;
}

export default function App() {
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [library, setLibrary] = useState<LibraryEntry[]>([]);
  const [entry, setEntry] = useState<LibraryEntry | null>(null);
  const [book, setBook] = useState<Book | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);

  const entryIdRef = useRef<string | null>(null);
  useEffect(() => {
    entryIdRef.current = entry?.id ?? null;
  }, [entry]);

  useEffect(() => setLibrary(loadLibrary()), []);

  // O drawer da biblioteca fecha no Esc — quem navega por teclado não fica
  // preso atrás dele.
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (ev: KeyboardEvent) => ev.key === "Escape" && setDrawerOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  // Monitora o backend (sobe via `uv run uvicorn main:app` no diretório backend).
  useEffect(() => {
    let alive = true;
    const ping = () => checkHealth().then((ok) => alive && setBackendUp(ok));
    ping();
    const t = setInterval(ping, 5000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const paras = useMemo(() => (book ? flatten(book) : []), [book]);

  const openBookFromPath = useCallback(async (path: string, existing?: LibraryEntry) => {
    setBusy(true);
    setError(null);
    setDrawerOpen(false);
    try {
      const b = await extractBook(path);
      const flat = flatten(b);
      const e: LibraryEntry = existing
        ? { ...existing, totalParas: flat.length }
        : {
            id: path,
            path,
            title: b.title || path.split(/[/\\]/).pop() || "Sem título",
            author: b.author,
            format: b.source_format,
            engine: "piper",
            voice: DEFAULT_VOICE,
            progressIndex: 0,
            totalParas: flat.length,
            addedAt: Date.now(),
          };
      setLibrary(upsertEntry(e));
      setEntry(e);
      setBook(b);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao abrir o livro");
    } finally {
      setBusy(false);
    }
  }, []);

  const pickFile = useCallback(async () => {
    const selected = await open({
      multiple: false,
      filters: [{ name: "Livros", extensions: ["pdf", "epub"] }],
    });
    if (typeof selected === "string") await openBookFromPath(selected);
  }, [openBookFromPath]);

  const handleProgress = useCallback((i: number) => {
    setEntry((prev) => (prev ? { ...prev, progressIndex: i } : prev));
    setLibrary((prev) => {
      const lib = prev.map((e) => (e.id === entryIdRef.current ? { ...e, progressIndex: i } : e));
      saveLibrary(lib);
      return lib;
    });
  }, []);

  const handleSettings = useCallback((engine: string, voice: string | null) => {
    setEntry((prev) => (prev ? { ...prev, engine, voice } : prev));
    setLibrary((prev) => {
      const lib = prev.map((e) => (e.id === entryIdRef.current ? { ...e, engine, voice } : e));
      saveLibrary(lib);
      return lib;
    });
  }, []);

  function deleteEntry(id: string) {
    setLibrary(removeEntry(id));
    if (entryIdRef.current === id) {
      setEntry(null);
      setBook(null);
    }
  }

  function startRename(e: LibraryEntry) {
    setEditingId(e.id);
    setDraft(e.title);
  }

  function commitRename() {
    if (!editingId) return;
    const title = draft.trim();
    if (title) {
      setLibrary(renameEntry(editingId, title));
      setEntry((prev) => (prev && prev.id === editingId ? { ...prev, title } : prev));
    }
    setEditingId(null);
  }

  const win = getCurrentWindow();
  const backend = BACKEND_STATE[backendUp == null ? "checking" : backendUp ? "up" : "down"];

  return (
    <div className="root">
      <div className="titlebar" data-tauri-drag-region>
        <div className="tb-brand" data-tauri-drag-region>
          <img src={logoUrl} className="tb-logo" alt="" draggable={false} />
          <span>incipit</span>
        </div>
        <div className="tb-controls">
          <button className="tb-btn" onClick={() => win.minimize()} title="Minimizar" aria-label="Minimizar">
            <svg viewBox="0 0 10 10" width="10" height="10"><path d="M0 5h10" stroke="currentColor" strokeWidth="1.2" /></svg>
          </button>
          <button className="tb-btn" onClick={() => win.toggleMaximize()} title="Maximizar" aria-label="Maximizar">
            <svg viewBox="0 0 10 10" width="10" height="10"><rect x="0.6" y="0.6" width="8.8" height="8.8" fill="none" stroke="currentColor" strokeWidth="1.2" /></svg>
          </button>
          <button className="tb-btn close" onClick={() => win.close()} title="Fechar" aria-label="Fechar">
            <svg viewBox="0 0 10 10" width="10" height="10"><path d="M0 0l10 10M10 0L0 10" stroke="currentColor" strokeWidth="1.2" /></svg>
          </button>
        </div>
      </div>

      <div className="app">
        <aside id="library" className={`sidebar${drawerOpen ? " open" : ""}`}>
          <div className="brand">
            <img src={logoUrl} className="brand-logo" alt="" draggable={false} />
            <div className="brand-text">
              <span className="logo">incipit</span>
              <small>leitor por voz</small>
            </div>
          </div>

          <button className="open-btn" onClick={pickFile} disabled={busy}>
            {busy ? "Abrindo…" : "+ Abrir livro"}
          </button>

          <ul className="lib">
            {library.length === 0 && (
              <li className="lib-empty">
                <strong>Sua biblioteca está vazia.</strong>
                Abra um PDF ou EPUB e ele fica guardado aqui, com o ponto onde você parou.
              </li>
            )}
            {library.map((e) => {
              const pct = e.totalParas ? Math.round((e.progressIndex / e.totalParas) * 100) : 0;
              return (
                <li key={e.id} className={`lib-item${entry?.id === e.id ? " active" : ""}`}>
                  {editingId === e.id ? (
                    <input
                      className="lib-edit"
                      value={draft}
                      autoFocus
                      aria-label="Novo título do livro"
                      onChange={(ev) => setDraft(ev.target.value)}
                      onBlur={commitRename}
                      onKeyDown={(ev) => {
                        if (ev.key === "Enter") commitRename();
                        if (ev.key === "Escape") setEditingId(null);
                      }}
                    />
                  ) : (
                    <button
                      className="lib-open"
                      onClick={() => openBookFromPath(e.path, e)}
                      onDoubleClick={() => startRename(e)}
                      aria-current={entry?.id === e.id ? "true" : undefined}
                    >
                      <span className="lib-title">{e.title}</span>
                      {e.author && <span className="lib-author">{e.author}</span>}
                      <span className="lib-meta">
                        <span className="lib-format">{e.format.toUpperCase()}</span>
                        <span className="lib-track">
                          <span className="lib-fill" style={{ width: `${pct}%` }} />
                        </span>
                        <span>{pct}% lido</span>
                      </span>
                    </button>
                  )}
                  <div className="lib-actions">
                    <button
                      className="lib-icon"
                      onClick={() => startRename(e)}
                      title={`Renomear ${e.title}`}
                      aria-label={`Renomear ${e.title}`}
                    >
                      ✎
                    </button>
                    <button
                      className="lib-icon del"
                      onClick={() => deleteEntry(e.id)}
                      title={`Remover ${e.title}`}
                      aria-label={`Remover ${e.title}`}
                    >
                      ✕
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>

          <p className={`backend ${backend.className}`} data-testid="backend-status" role="status">
            <span className="backend-dot" aria-hidden="true" />
            <span className="backend-label">{backend.label}</span>
          </p>
        </aside>

        {drawerOpen && (
          <button
            type="button"
            className="drawer-scrim"
            data-testid="library-close"
            aria-label="Fechar biblioteca"
            onClick={() => setDrawerOpen(false)}
          />
        )}

        <main className="main">
          {/* Só aparece abaixo do breakpoint, onde a biblioteca vira drawer. */}
          <button
            type="button"
            className="drawer-toggle"
            data-testid="library-toggle"
            aria-controls="library"
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen(true)}
          >
            <svg viewBox="0 0 14 12" width="14" height="12" aria-hidden="true">
              <path d="M0 1h14M0 6h14M0 11h14" stroke="currentColor" strokeWidth="1.6" />
            </svg>
            Biblioteca
          </button>

          <div className="notices">
            {error && (
              <Notice kind="error" title="Não foi possível abrir o livro" onDismiss={() => setError(null)}>
                {error}
              </Notice>
            )}
            {backendUp === false && (
              <Notice kind="warn" title="Backend offline">
                Ele sobe junto com o app e pode levar alguns segundos para iniciar. Se persistir,
                reabra o app.
              </Notice>
            )}
          </div>

          {busy ? (
            <ExtractSkeleton />
          ) : entry && book ? (
            <Reader
              key={entry.id}
              entry={entry}
              paras={paras}
              onProgress={handleProgress}
              onSettings={handleSettings}
            />
          ) : (
            <div className="welcome">
              <img src={logoUrl} className="welcome-logo" alt="" draggable={false} />
              <h1>incipit</h1>
              <p>Abra um PDF ou EPUB para começar a ouvir.</p>
              <button className="open-btn big" onClick={pickFile} disabled={busy}>
                {busy ? "Abrindo…" : "+ Abrir livro"}
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
