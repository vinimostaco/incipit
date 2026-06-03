// Persistência da biblioteca e do progresso em localStorage.
import type { LibraryEntry } from "./types";

const KEY = "incipit.library";

export function loadLibrary(): LibraryEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as LibraryEntry[]) : [];
  } catch {
    return [];
  }
}

export function saveLibrary(lib: LibraryEntry[]): void {
  localStorage.setItem(KEY, JSON.stringify(lib));
}

export function upsertEntry(entry: LibraryEntry): LibraryEntry[] {
  const lib = loadLibrary();
  const i = lib.findIndex((e) => e.id === entry.id);
  if (i >= 0) lib[i] = entry;
  else lib.unshift(entry);
  saveLibrary(lib);
  return lib;
}

export function renameEntry(id: string, title: string): LibraryEntry[] {
  const lib = loadLibrary().map((e) => (e.id === id ? { ...e, title } : e));
  saveLibrary(lib);
  return lib;
}

export function removeEntry(id: string): LibraryEntry[] {
  const lib = loadLibrary().filter((e) => e.id !== id);
  saveLibrary(lib);
  return lib;
}
