"""Caminhos de dados do incipit (modelos de voz e cache de áudio).

Tudo fica sob INCIPIT_DATA_DIR (padrão: ~/.local/share/incipit), fora do
repositório, para não versionar modelos pesados nem áudio gerado.

Este módulo só *calcula* caminhos — não cria nenhum diretório. Importar o
pacote é uma operação de leitura: quem grava (`tts.cache.put`, `tts.piper._load`)
cria o diretório de que precisa, na hora em que precisa. Fazer o `mkdir` aqui
significava que qualquer import — incluindo o de uma ferramenta que só queria
inspecionar o pacote — escrevia no disco, e que um caminho não-gravável
derrubava o backend ainda no import: como o sidecar é um processo separado
lançado pelo Tauri, isso aparece para o usuário como um app que nunca termina
de abrir, sem erro nenhum na tela.
"""

from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(
    os.environ.get("INCIPIT_DATA_DIR", Path.home() / ".local" / "share" / "incipit")
).expanduser()

MODELS_DIR = DATA_DIR / "models"
AUDIO_CACHE_DIR = DATA_DIR / "tts-cache"
