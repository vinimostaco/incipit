import type * as React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";

import { checkHealth, extractBook } from "./api";
import { Reader } from "./Reader";
import { loadLibrary, removeEntry, saveLibrary, upsertEntry } from "./storage";
import type { Book, FlatPara, LibraryEntry } from "./types";
import "./App.css";

const DEFAULT_VOICE = "pt_BR-faber-medium";

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

  const entryIdRef = useRef<string | null>(null);
  useEffect(() => {
    entryIdRef.current = entry?.id ?? null;
  }, [entry]);

  useEffect(() => setLibrary(loadLibrary()), []);

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

  function deleteEntry(ev: React.MouseEvent, id: string) {
    ev.stopPropagation();
    setLibrary(removeEntry(id));
    if (entryIdRef.current === id) {
      setEntry(null);
      setBook(null);
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">incipit</span>
          <small>leitor por voz</small>
        </div>

        <button className="open-btn" onClick={pickFile} disabled={busy}>
          {busy ? "Abrindo…" : "+ Abrir livro"}
        </button>

        <div className="lib">
          {library.length === 0 && <p className="lib-empty">Sua biblioteca está vazia.</p>}
          {library.map((e) => {
            const pct = e.totalParas ? Math.round((e.progressIndex / e.totalParas) * 100) : 0;
            return (
              <div
                key={e.id}
                className={`lib-item${entry?.id === e.id ? " active" : ""}`}
                onClick={() => openBookFromPath(e.path, e)}
              >
                <div className="lib-info">
                  <span className="lib-title">{e.title}</span>
                  {e.author && <span className="lib-author">{e.author}</span>}
                  <span className="lib-progress">
                    {e.format.toUpperCase()} · {pct}%
                  </span>
                </div>
                <button className="lib-del" onClick={(ev) => deleteEntry(ev, e.id)} title="Remover">
                  ✕
                </button>
              </div>
            );
          })}
        </div>

        <div className={`backend ${backendUp ? "up" : backendUp === false ? "down" : ""}`}>
          {backendUp == null && "verificando backend…"}
          {backendUp === true && "● backend online"}
          {backendUp === false && "● backend offline"}
        </div>
      </aside>

      <main className="main">
        {error && <div className="banner error">{error}</div>}
        {backendUp === false && (
          <div className="banner warn">
            Backend offline — ele sobe junto com o app e pode levar alguns
            segundos para iniciar. Se persistir, reabra o app.
          </div>
        )}

        {entry && book ? (
          <Reader
            key={entry.id}
            entry={entry}
            paras={paras}
            onProgress={handleProgress}
            onSettings={handleSettings}
          />
        ) : (
          <div className="welcome">
            <h1>incipit</h1>
            <p>Abra um PDF ou EPUB para começar a ouvir.</p>
            <button className="open-btn big" onClick={pickFile} disabled={busy}>
              {busy ? "Abrindo…" : "+ Abrir livro"}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
