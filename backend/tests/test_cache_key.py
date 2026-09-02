"""`cache_key` é o contrato do cache progressivo de áudio.

Duas propriedades importam, e as duas custam caro se quebrarem numa sessão de
escuta longa: se a chave não for determinística, o cache nunca dá hit e cada
parágrafo é sintetizado de novo (latência e CPU no meio do livro); se ela
colidir entre parâmetros diferentes, o usuário troca de voz e continua ouvindo
a voz antiga — ou pior, ouve um parágrafo trocado.
"""

from __future__ import annotations

import itertools

import pytest

from incipit.tts.cache import cache_key, cache_path

BASE = ("piper", "Era uma vez uma casa de treze janelas.", "pt_BR-faber-medium", "pt", 1.0)


def test_is_deterministic() -> None:
    """Mesma entrada, mesma chave — inclusive entre chamadas separadas."""
    assert cache_key(*BASE) == cache_key(*BASE)
    assert len({cache_key(*BASE) for _ in range(50)}) == 1


def test_is_a_sha256_hexdigest() -> None:
    key = cache_key(*BASE)
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


@pytest.mark.parametrize(
    ("pos", "other"),
    [
        (0, "xtts"),                                   # engine
        (1, "Era uma vez uma casa de treze janelas!"),  # text
        (2, "pt_BR-cadu-medium"),                      # voice
        (3, "en"),                                     # language
        (4, 1.25),                                     # speed
    ],
    ids=["engine", "text", "voice", "language", "speed"],
)
def test_each_of_the_five_components_changes_the_key(pos: int, other: object) -> None:
    """Trocar qualquer um dos 5 componentes tem de mudar o hash."""
    changed = list(BASE)
    changed[pos] = other
    assert cache_key(*changed) != cache_key(*BASE)


def test_all_five_are_pairwise_distinct() -> None:
    """As 5 variações, comparadas entre si, também são todas diferentes — não
    basta cada uma diferir da base."""
    variants = [
        cache_key("xtts", BASE[1], BASE[2], BASE[3], BASE[4]),
        cache_key(BASE[0], "outro texto", BASE[2], BASE[3], BASE[4]),
        cache_key(BASE[0], BASE[1], "pt_BR-cadu-medium", BASE[3], BASE[4]),
        cache_key(BASE[0], BASE[1], BASE[2], "en", BASE[4]),
        cache_key(BASE[0], BASE[1], BASE[2], BASE[3], 1.25),
    ]
    assert len(set(variants)) == len(variants)


def test_voice_none_differs_from_voice_named() -> None:
    """`voice=None` (deixa o engine escolher o padrão) não pode colidir com o
    nome literal da voz padrão — são chamadas diferentes."""
    assert cache_key("piper", BASE[1], None, "pt", 1.0) != cache_key(*BASE)


def test_speed_is_compared_at_three_decimals() -> None:
    """A velocidade entra formatada com 3 casas: 1.0 e 1.0004 são a mesma
    chave, 1.0 e 1.001 não são. Isso é de propósito — impede que ruído de
    ponto flutuante vindo do slider da UI invalide o cache inteiro."""
    assert cache_key("piper", BASE[1], BASE[2], "pt", 1.0) == cache_key(
        "piper", BASE[1], BASE[2], "pt", 1.0004
    )
    assert cache_key("piper", BASE[1], BASE[2], "pt", 1.0) != cache_key(
        "piper", BASE[1], BASE[2], "pt", 1.001
    )


def test_no_collision_from_field_boundaries() -> None:
    """Os campos são separados por \\x00 na serialização. Estas entradas só
    colidiriam se a fronteira entre campos pudesse ser forjada movendo texto de
    um campo para o outro."""
    a = cache_key("piper", "b", "voz", "pt", 1.0)
    b = cache_key("piper", "", "voz", "pt", 1.0)
    c = cache_key("piperb", "", "voz", "pt", 1.0)
    assert len({a, b, c}) == 3


def test_cache_path_is_a_wav_named_after_the_key(data_dir) -> None:
    key = cache_key(*BASE)
    path = cache_path(key)
    assert path.name == f"{key}.wav"
    assert path.parent == data_dir / "tts-cache"


def test_distinct_inputs_give_distinct_paths() -> None:
    """Fecha o laço: chaves diferentes têm de virar arquivos diferentes."""
    engines, speeds = ["piper", "xtts"], [1.0, 1.5]
    paths = {
        cache_path(cache_key(e, "texto", "voz", "pt", s))
        for e, s in itertools.product(engines, speeds)
    }
    assert len(paths) == 4
