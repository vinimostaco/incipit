"""Goldens de extração: congela o `Book` que cada fixture produz HOJE.

Esta é a rede de segurança do `extract.py` — ele não foi alterado para que
estes arquivos fossem gerados, e é justamente por isso que eles valem: o que
está em `golden/` é o comportamento real do código na versão travada em
`uv.lock`, verrugas incluídas, não o comportamento que gostaríamos que ele
tivesse. Duas verrugas que os goldens deliberadamente registram:

* **PDF: parágrafo == página.** O `pypdf` não emite linha em branco por salto
  vertical, e `_paragraphs_from_text` só separa parágrafos em linha em branco.
  A única fronteira que sobra num PDF é a virada de página, onde `extract_pdf`
  junta o texto com "\\n\\n". Por isso `com-outline.pdf` tem capítulos de duas
  páginas: é o menor jeito de ter mais de um parágrafo por capítulo.
* **EPUB: quebras de linha sobrevivem dentro do parágrafo.** `_WS` só colapsa
  espaço e tab, não `\\n`, então o `\\n` do fonte XHTML fica no texto extraído.
* **EPUB: o `nav.xhtml` vira um capítulo.** Ele é um ITEM_DOCUMENT como
  qualquer outro, então o sumário do EPUB 3 entra no fim do livro como um
  capítulo cujos "parágrafos" são os títulos dos outros capítulos.

Se um golden quebrar, a pergunta certa é "a mudança de comportamento é
desejada?" — e não "como faço o teste passar?". Para regravar depois de decidir
que sim:

    uv run pytest tests/test_extract_golden.py --update-goldens
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from incipit.extract import extract

from .conftest import FIXTURES, GOLDEN

# (arquivo de fixture, nome do golden)
CASES = [
    ("com-outline.pdf", "com-outline.json"),
    ("sem-outline.pdf", "sem-outline.json"),
    ("paragrafos-simples.epub", "paragrafos-simples.json"),
    ("citacoes-e-listas.epub", "citacoes-e-listas.json"),
]


def _dump(book) -> str:
    return json.dumps(book.model_dump(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


@pytest.mark.parametrize(("fixture", "golden"), CASES)
def test_extract_matches_golden(fixture: str, golden: str, update_goldens: bool) -> None:
    book = extract(str(FIXTURES / fixture))
    got = _dump(book)
    path = GOLDEN / golden

    if update_goldens:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(got, encoding="utf-8")
        pytest.skip(f"golden regravado: {path.name}")

    assert path.is_file(), (
        f"golden ausente: {path}. Gere com "
        f"`uv run pytest tests/test_extract_golden.py --update-goldens`."
    )
    assert got == path.read_text(encoding="utf-8"), (
        f"a extração de {fixture} mudou em relação ao golden {golden}"
    )


@pytest.mark.parametrize(("fixture", "golden"), CASES)
def test_golden_is_plausible_as_a_book(fixture: str, golden: str, update_goldens: bool) -> None:
    """Um golden pode passar e ainda ser lixo, se tiver sido congelado de uma
    execução ruim. Estas asserções são o piso: o livro tem capítulo, o capítulo
    tem parágrafo, e o parágrafo tem prosa de verdade — não uma string vazia
    nem três caracteres de sujeira de encoding."""
    if update_goldens:
        pytest.skip("regravando goldens")

    data = json.loads((GOLDEN / golden).read_text(encoding="utf-8"))

    assert data["source_format"] in ("pdf", "epub")
    assert data["title"], "livro sem título"
    assert data["chapters"], "livro sem nenhum capítulo"

    total_chars = 0
    for chapter in data["chapters"]:
        assert chapter["paragraphs"], f"capítulo {chapter['index']} sem parágrafos"
        for para in chapter["paragraphs"]:
            text = para["text"]
            assert text.strip(), "parágrafo vazio"
            # � é o que o "replace" de decodificação deixa para trás
            assert "�" not in text, f"sujeira de encoding em: {text[:60]!r}"
            total_chars += len(text)

    assert total_chars > 200, f"só {total_chars} caracteres — extração provavelmente vazia"

    # índices contíguos a partir de zero, dentro do capítulo e entre capítulos
    assert [c["index"] for c in data["chapters"]] == list(range(len(data["chapters"])))
    for chapter in data["chapters"]:
        expected = list(range(len(chapter["paragraphs"])))
        assert [p["index"] for p in chapter["paragraphs"]] == expected


def test_pdf_outline_becomes_chapters() -> None:
    """O PDF com sumário se divide pelos capítulos do sumário; o sem sumário
    cai no capítulo único. É o par de caminhos que `extract_pdf` decide."""
    with_outline = extract(str(FIXTURES / "com-outline.pdf"))
    assert [c.title for c in with_outline.chapters] == [
        "Capitulo I - A casa vazia",
        "Capitulo II - O inventario",
        "Capitulo III - Dezembro",
    ]

    without = extract(str(FIXTURES / "sem-outline.pdf"))
    assert len(without.chapters) == 1
    assert without.chapters[0].title is None


def test_pdf_metadata_falls_back_to_filename() -> None:
    """Com /Info, o título vem do PDF; sem /Info, vem do nome do arquivo."""
    assert extract(str(FIXTURES / "com-outline.pdf")).title == "A casa de treze janelas"
    assert extract(str(FIXTURES / "com-outline.pdf")).author == "Fixture do incipit"

    bare = extract(str(FIXTURES / "sem-outline.pdf"))
    assert bare.title == "sem-outline"
    assert bare.author is None


def test_pdf_rejoins_hyphenated_line_break() -> None:
    """"silen-\\ncio" na quebra de linha do PDF vira "silencio" no parágrafo."""
    book = extract(str(FIXTURES / "com-outline.pdf"))
    corpo = " ".join(p.text for c in book.chapters for p in c.paragraphs)
    assert "silencio" in corpo
    assert "silen-" not in corpo


def test_epub_collects_blockquotes_and_list_items() -> None:
    """Num EPUB, <blockquote> e <li> contam como parágrafo — mas um bloco que
    aninha outro bloco é container e não entra duas vezes."""
    book = extract(str(FIXTURES / "citacoes-e-listas.epub"))
    textos = [p.text for c in book.chapters for p in c.paragraphs]

    # citação com <p> dentro: entra o <p> interno, não o <blockquote> externo
    assert sum("uma com os olhos, outra com o" in t for t in textos) == 1
    # citação sem <p> dentro: o próprio <blockquote> é a folha
    assert "Uma citacao curta, sem paragrafo por dentro." in textos
    # itens de lista viram parágrafos independentes
    assert "o audio nao pode engasgar entre paragrafos;" in textos
    assert "a primeira frase precisa soar rapido;" in textos


def test_unsupported_and_missing_paths_raise() -> None:
    with pytest.raises(FileNotFoundError):
        extract(str(FIXTURES / "nao-existe.pdf"))

    with pytest.raises(ValueError, match="Formato não suportado"):
        extract(str(Path(__file__)))  # .py
