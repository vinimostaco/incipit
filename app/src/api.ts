// Cliente do backend local (FastAPI em 127.0.0.1:8765).
import type { Book } from "./types";

const BASE = "http://127.0.0.1:8765";

async function detailError(r: Response): Promise<never> {
  const body = await r.json().catch(() => null);
  throw new Error(body?.detail || `Erro ${r.status} (${r.statusText})`);
}

export async function checkHealth(): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/health`);
    return r.ok;
  } catch {
    return false;
  }
}

export async function extractBook(path: string): Promise<Book> {
  const r = await fetch(`${BASE}/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!r.ok) await detailError(r);
  return r.json();
}

// Sempre pede speed=1.0; a velocidade de escuta é controlada no cliente via
// playbackRate (instantâneo e sem inflar o cache do backend).
export async function synthesize(
  text: string,
  engine: string,
  voice: string | null,
): Promise<Blob> {
  const r = await fetch(`${BASE}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, engine, voice, language: "pt", speed: 1.0 }),
  });
  if (!r.ok) await detailError(r);
  return r.blob();
}
