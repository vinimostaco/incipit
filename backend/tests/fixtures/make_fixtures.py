#!/usr/bin/env python3
"""Gera os fixtures de extração (2 PDFs + 2 EPUBs).

Os arquivos gerados são versionados; este script existe para que eles sejam
auditáveis e reproduzíveis, não para rodar no CI. Rode-o à mão quando quiser
recriar ou acrescentar um fixture:

    uv run python tests/fixtures/make_fixtures.py

O texto é original, escrito para os testes — nenhum trecho vem de obra de
terceiros, então os fixtures são livres de direitos.

O escritor de PDF é mínimo e sem dependências de propósito: gerar os PDFs com
uma biblioteca pesada (reportlab) só para produzir quatro arquivinhos tornaria
o fixture menos legível e amarraria o repo a mais uma dependência de dev.
"""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent

# --------------------------------------------------------------------------- #
# Texto (original, escrito para os fixtures)
# --------------------------------------------------------------------------- #

# Cada capítulo ocupa DUAS páginas. Isso é de propósito: o pypdf não emite linha
# em branco por salto vertical (verificado na versão travada no uv.lock), então a
# única fronteira de parágrafo que sobrevive num PDF é a virada de página — que é
# onde `extract_pdf` junta o texto com "\n\n". Um capítulo de duas páginas é,
# portanto, o menor fixture que produz mais de um parágrafo por capítulo e que
# exercita o fatiamento por faixa de páginas do outline.
#
# A palavra hifenizada no fim da linha ("silen-/cio") exercita `_HYPHEN_BREAK`;
# as quebras de linha dentro de cada bloco exercitam a junção de linhas de
# `_paragraphs_from_text`.
PDF_OUTLINE_CHAPTERS: list[tuple[str, list[list[str]]]] = [
    (
        "Capitulo I - A casa vazia",
        [
            [
                "A casa que herdei tinha treze janelas e nenhuma cortina. Os",
                "primeiros dias foram de inventario: contei os degraus, contei as",
                "macanetas, contei ate as rachaduras do reboco, como quem procura",
                "um erro de soma que explique o resto.",
            ],
            [
                "Foi so na terceira noite que reparei no silen-",
                "cio. Nao era a ausencia de som; era um som proprio, espesso, que",
                "se acomodava nos comodos vazios como poeira.",
            ],
        ],
    ),
    (
        "Capitulo II - O inventario",
        [
            [
                "Meu tio guardava tudo em caixas de charuto: recibos, botoes, uma",
                "chave sem fechadura conhecida. Abri as caixas em ordem alfabetica,",
                "porque ele as havia rotulado, e porque nao me ocorreu outra ordem.",
            ],
            [
                "Na caixa marcada com a letra M encontrei um bilhete dobrado em",
                "quatro. Dizia apenas: nao venda a casa antes de dezembro. Nao havia",
                "assinatura, nem ano.",
            ],
        ],
    ),
    (
        "Capitulo III - Dezembro",
        [
            [
                "Esperei. Nao por obediencia, mas porque esperar era, naquele",
                "momento, a unica coisa que a casa me pedia com clareza.",
            ],
            [
                "Em dezembro as treze janelas amanheceram embacadas ao mesmo tempo,",
                "e entendi o bilhete. Ou pelo menos entendi o bastante para nao",
                "vender a casa.",
            ],
        ],
    ),
]

PDF_FLAT_PAGES: list[list[list[str]]] = [
    [
        [
            "Relatorio de uma travessia curta, escrito sem sumario, sem divisoes e",
            "sem qualquer pretensao de virar livro.",
        ],
        [
            "Saimos as seis da manha. O rio estava mais baixo do que o esperado, o",
            "que tornou a primeira hora um exercicio de paciencia e de empurrao.",
        ],
    ],
    [
        [
            "Ao meio-dia paramos numa curva onde a agua fazia sombra. Comemos em",
            "silencio, cada um olhando para um ponto diferente da margem.",
        ],
        [
            "Chegamos antes do anoitecer. Ninguem anotou a hora exata, e por isso",
            "este relatorio termina sem numero.",
        ],
    ],
]

EPUB_SIMPLE_DOCS: list[tuple[str, str]] = [
    (
        "Primeira parte",
        """
        <h1>Primeira parte</h1>
        <p>Havia no fundo do quintal uma figueira que ninguem plantou. Ela
        simplesmente estava la, mais velha que a casa e mais teimosa que o muro.</p>
        <p>Meu avo dizia que arvore nascida sozinha nao se poda. Nunca explicou o
        motivo, e nunca precisou: bastava o tom com que dizia.</p>
        <p>No verao a figueira dava sombra suficiente para tres cadeiras. No
        inverno dava galho seco, que meu avo recolhia sem reclamar.</p>
        """,
    ),
    (
        "Segunda parte",
        """
        <h1>Segunda parte</h1>
        <p>Quando o muro caiu, ninguem culpou a figueira. Culparam a chuva, que
        era mais facil de culpar e nao morava no quintal.</p>
        <p>Levantamos o muro dois metros adiante, contornando a raiz. A figueira
        ficou, entao, com um pedaco de calcada so dela.</p>
        """,
    ),
]

EPUB_RICH_DOCS: list[tuple[str, str]] = [
    (
        "Sobre a leitura em voz alta",
        """
        <h1>Sobre a leitura em voz alta</h1>
        <p>Ler em voz alta e uma tecnologia antiga o bastante para parecer
        natural, e recente o bastante para ainda estar em disputa.</p>
        <blockquote>
          <p>Quem le em voz alta le duas vezes: uma com os olhos, outra com o
          folego.</p>
        </blockquote>
        <p>A citacao acima esta dentro de um bloco que contem outro bloco. O
        extrator precisa decidir qual dos dois e a folha.</p>
        <blockquote>Uma citacao curta, sem paragrafo por dentro.</blockquote>
        <p>Os requisitos de uma sessao longa de escuta sao poucos e teimosos:</p>
        <ul>
          <li>o audio nao pode engasgar entre paragrafos;</li>
          <li>a primeira frase precisa soar rapido;</li>
          <li>o app nao pode morrer no meio do livro.</li>
        </ul>
        <p>Cada item acima e um bloco folha independente.</p>
        """,
    ),
    (
        "Notas de rodape do capitulo",
        """
        <h2>Notas de rodape do capitulo</h2>
        <ol>
          <li>A primeira nota trata de uma edicao que nunca existiu.</li>
          <li>A segunda nota corrige a primeira.</li>
        </ol>
        <blockquote>
          <p>A terceira nota foi perdida, e por isso e a mais citada.</p>
        </blockquote>
        """,
    ),
]


# --------------------------------------------------------------------------- #
# Escritor de PDF mínimo (Helvetica / WinAnsiEncoding, streams sem compressão)
# --------------------------------------------------------------------------- #
PAGE_W, PAGE_H = 595, 842
MARGIN_X, TOP_Y = 60, 780
FONT_SIZE, LEADING = 11, 16


def _esc(s: str) -> bytes:
    b = s.encode("cp1252", errors="replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _content_stream(paragraphs: list[list[str]], title: str | None) -> bytes:
    """Uma linha de texto por operador Tj, parágrafos separados por um T* vazio.

    O T* extra é o que faz o pypdf enxergar linha em branco entre parágrafos —
    e linha em branco é o que `_paragraphs_from_text` usa para separá-los.
    """
    parts = [b"BT", f"/F1 {FONT_SIZE} Tf".encode(), f"{LEADING} TL".encode(),
             f"{MARGIN_X} {TOP_Y} Td".encode()]
    blocks: list[list[str]] = ([[title]] if title else []) + list(paragraphs)
    for i, block in enumerate(blocks):
        if i:
            parts.append(b"T*")  # linha em branco entre blocos
        for line in block:
            parts.append(b"(" + _esc(line) + b") Tj")
            parts.append(b"T*")
    parts.append(b"ET")
    return b"\n".join(parts)


def write_pdf(
    dest: Path,
    pages: list[bytes],
    outline: list[tuple[str, int]],
    info: tuple[str, str] | None = None,
) -> None:
    """Monta um PDF com `pages` (content streams já prontos), um /Outlines
    opcional apontando `titulo -> indice de pagina` e um /Info opcional
    (título, autor) — sem /Info, `extract_pdf` cai no nome do arquivo."""
    objects: dict[int, bytes] = {}
    n_pages = len(pages)

    font_id = 3
    page_ids = [font_id + 1 + i for i in range(n_pages)]
    content_ids = [page_ids[-1] + 1 + i for i in range(n_pages)]
    outlines_id = content_ids[-1] + 1
    item_ids = [outlines_id + 1 + i for i in range(len(outline))]
    info_id = (item_ids[-1] if item_ids else outlines_id) + 1

    catalog = f"<< /Type /Catalog /Pages 2 0 R{f' /Outlines {outlines_id} 0 R' if outline else ''} >>"
    objects[1] = catalog.encode()
    if info:
        objects[info_id] = (
            b"<< /Title (" + _esc(info[0]) + b") /Author (" + _esc(info[1]) + b") >>"
        )
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode()
    objects[font_id] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>"
    )
    for pid, cid in zip(page_ids, content_ids):
        objects[pid] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {cid} 0 R >>"
        ).encode()
    for cid, stream in zip(content_ids, pages):
        objects[cid] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    if outline:
        objects[outlines_id] = (
            f"<< /Type /Outlines /First {item_ids[0]} 0 R "
            f"/Last {item_ids[-1]} 0 R /Count {len(outline)} >>"
        ).encode()
        for i, (title, page_idx) in enumerate(outline):
            links = f" /Parent {outlines_id} 0 R"
            if i:
                links += f" /Prev {item_ids[i - 1]} 0 R"
            if i + 1 < len(item_ids):
                links += f" /Next {item_ids[i + 1]} 0 R"
            objects[item_ids[i]] = (
                b"<< /Title (" + _esc(title) + b") "
                + f"/Dest [{page_ids[page_idx]} 0 R /XYZ null null null]{links} >>".encode()
            )

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + objects[num] + b"\nendobj\n"

    xref_at = len(out)
    max_id = max(objects)
    out += f"xref\n0 {max_id + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, max_id + 1):
        out += f"{offsets.get(num, 0):010d} 00000 n \n".encode()
    info_ref = f" /Info {info_id} 0 R" if info else ""
    out += (
        f"trailer\n<< /Size {max_id + 1} /Root 1 0 R{info_ref} >>\nstartxref\n{xref_at}\n"
    ).encode() + b"%%EOF\n"

    dest.write_bytes(bytes(out))
    print(f"  {dest.name}: {len(out)} bytes, {n_pages} paginas, {len(outline)} outline")


# --------------------------------------------------------------------------- #
# EPUB
# --------------------------------------------------------------------------- #
def write_epub(dest: Path, title: str, author: str, uid: str,
               docs: list[tuple[str, str]]) -> None:
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier(uid)
    book.set_title(title)
    book.set_language("pt")
    book.add_author(author)

    items = []
    for i, (chap_title, body) in enumerate(docs, start=1):
        item = epub.EpubHtml(title=chap_title, file_name=f"cap{i}.xhtml", lang="pt")
        item.content = f"<html><head><title>{chap_title}</title></head><body>{body}</body></html>"
        book.add_item(item)
        items.append(item)

    book.toc = tuple(items)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *items]
    epub.write_epub(str(dest), book)
    print(f"  {dest.name}: {dest.stat().st_size} bytes, {len(docs)} documentos")


def main() -> None:
    print("PDFs:")
    # Com outline: cada capítulo ocupa duas páginas (um bloco por página), e a
    # entrada do sumário aponta para a primeira delas. O título do capítulo é
    # impresso na página de abertura, como num livro de verdade.
    pages: list[bytes] = []
    outline: list[tuple[str, int]] = []
    for title, blocks in PDF_OUTLINE_CHAPTERS:
        outline.append((title, len(pages)))
        for i, block in enumerate(blocks):
            pages.append(_content_stream([block], title if i == 0 else None))
    write_pdf(
        FIXTURES / "com-outline.pdf",
        pages,
        outline,
        info=("A casa de treze janelas", "Fixture do incipit"),
    )

    # sem outline: nenhum /Outlines no catálogo -> extrator cai no capítulo único
    write_pdf(
        FIXTURES / "sem-outline.pdf",
        [_content_stream(paras, None) for paras in PDF_FLAT_PAGES],
        outline=[],
    )

    print("EPUBs:")
    write_epub(
        FIXTURES / "paragrafos-simples.epub",
        "A figueira do quintal",
        "Fixture do incipit",
        "incipit-fixture-paragrafos-simples",
        EPUB_SIMPLE_DOCS,
    )
    write_epub(
        FIXTURES / "citacoes-e-listas.epub",
        "Notas sobre leitura em voz alta",
        "Fixture do incipit",
        "incipit-fixture-citacoes-e-listas",
        EPUB_RICH_DOCS,
    )


if __name__ == "__main__":
    main()
