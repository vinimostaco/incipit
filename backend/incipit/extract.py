"""Extração de texto estruturado (capítulo/parágrafo) de PDFs e EPUBs."""

from __future__ import annotations

import re
from pathlib import Path

from .models import Book, Chapter, Paragraph

_WS = re.compile(r"[ \t ]+")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_MULTI_NL = re.compile(r"\n{2,}")


def extract(path_str: str) -> Book:
    """Despacha para o extrator certo conforme a extensão do arquivo."""
    path = Path(path_str).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf(path)
    if ext == ".epub":
        return extract_epub(path)
    raise ValueError(f"Formato não suportado: {ext or '(sem extensão)'} — use .pdf ou .epub")


# --------------------------------------------------------------------------- #
# Helpers de limpeza
# --------------------------------------------------------------------------- #
def _clean(text: str) -> str:
    # une palavras quebradas por hifenização no fim da linha ("exem-\nplo" -> "exemplo")
    return _HYPHEN_BREAK.sub(r"\1\2", text)


def _paragraphs_from_text(text: str) -> list[Paragraph]:
    """Quebra texto cru em parágrafos. Linhas em branco separam parágrafos;
    quebras simples dentro de um parágrafo são unidas."""
    text = _clean(text)
    out: list[Paragraph] = []
    for block in _MULTI_NL.split(text):
        joined = " ".join(line.strip() for line in block.splitlines() if line.strip())
        joined = _WS.sub(" ", joined).strip()
        if joined:
            out.append(Paragraph(index=len(out), text=joined))
    return out


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def extract_pdf(path: Path) -> Book:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    meta = reader.metadata
    title = (meta.title if meta else None) or path.stem
    author = meta.author if meta else None

    chapters = _pdf_chapters_from_outline(reader)
    if not chapters:
        # fallback: sem sumário utilizável, tudo vira um capítulo único
        full = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        paras = _paragraphs_from_text(full)
        chapters = [Chapter(index=0, title=None, paragraphs=paras)]

    return Book(title=title, author=author, source_format="pdf", chapters=chapters)


def _pdf_chapters_from_outline(reader) -> list[Chapter]:
    """Tenta usar o sumário (outline) do PDF para segmentar em capítulos.
    Retorna [] se não houver um sumário utilizável — o chamador faz fallback."""
    try:
        outline = reader.outline
    except Exception:
        return []
    if not outline:
        return []

    entries: list[tuple[str, int]] = []

    def walk(items):
        for it in items:
            if isinstance(it, list):
                walk(it)
                continue
            try:
                page = reader.get_destination_page_number(it)
                entries.append((str(it.title), int(page)))
            except Exception:
                continue

    walk(outline)
    if len(entries) < 2:
        return []

    entries.sort(key=lambda e: e[1])
    n_pages = len(reader.pages)
    chapters: list[Chapter] = []
    for ci, (title, start) in enumerate(entries):
        end = entries[ci + 1][1] if ci + 1 < len(entries) else n_pages
        end = max(end, start + 1)
        text = "\n\n".join(
            (reader.pages[p].extract_text() or "") for p in range(start, min(end, n_pages))
        )
        paras = _paragraphs_from_text(text)
        if paras:
            chapters.append(Chapter(index=len(chapters), title=title, paragraphs=paras))
    return chapters


# --------------------------------------------------------------------------- #
# EPUB
# --------------------------------------------------------------------------- #
def extract_epub(path: Path) -> Book:
    import ebooklib
    from bs4 import BeautifulSoup
    from ebooklib import epub

    book = epub.read_epub(str(path))

    def _meta(field: str) -> str | None:
        try:
            vals = book.get_metadata("DC", field)
            return vals[0][0] if vals else None
        except Exception:
            return None

    title = _meta("title") or path.stem
    author = _meta("creator")

    chapters: list[Chapter] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        heading = soup.find(["h1", "h2", "h3"])
        ch_title = heading.get_text(strip=True) if heading else None

        paras: list[Paragraph] = []
        for p in soup.find_all("p"):
            txt = _WS.sub(" ", p.get_text(" ", strip=True)).strip()
            if txt:
                paras.append(Paragraph(index=len(paras), text=txt))

        if paras:
            chapters.append(Chapter(index=len(chapters), title=ch_title, paragraphs=paras))

    return Book(title=title, author=author, source_format="epub", chapters=chapters)
