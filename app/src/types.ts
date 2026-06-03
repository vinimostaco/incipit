// Espelha os modelos do backend (incipit/models.py).
export interface Paragraph {
  index: number;
  text: string;
}

export interface Chapter {
  index: number;
  title: string | null;
  paragraphs: Paragraph[];
}

export interface Book {
  title: string | null;
  author: string | null;
  source_format: string;
  chapters: Chapter[];
}

// Parágrafo "achatado" para reprodução sequencial contínua.
export interface FlatPara {
  globalIndex: number;
  chapterIndex: number;
  chapterTitle: string | null;
  text: string;
}

// Entrada da biblioteca, persistida em localStorage.
export interface LibraryEntry {
  id: string; // = path do arquivo
  path: string;
  title: string;
  author: string | null;
  format: string;
  engine: string; // "piper" | "xtts"
  voice: string | null;
  progressIndex: number;
  totalParas: number;
  addedAt: number;
}
