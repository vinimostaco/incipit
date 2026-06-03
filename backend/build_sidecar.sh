#!/usr/bin/env bash
# Empacota o backend num binário único (PyInstaller) e o instala em
# app/src-tauri/binaries/ com o sufixo de target-triple que o Tauri espera.
#
# Build leve: venv isolado só com as deps base (sem xtts/PyTorch). Uso:
#   ./build_sidecar.sh                 # detecta o triple via rustc
#   ./build_sidecar.sh <target-triple> # força o triple (ex.: cross-compile)
set -euo pipefail
cd "$(dirname "$0")"  # backend/

# --- target triple (convenção de nome do sidecar do Tauri) ---
TRIPLE="${1:-}"
if [ -z "$TRIPLE" ]; then
  RUSTC="$(command -v rustc || echo "$HOME/.cargo/bin/rustc")"
  TRIPLE="$("$RUSTC" -vV | sed -n 's/^host: //p')"
fi
[ -n "$TRIPLE" ] || { echo "!! não consegui determinar o target-triple; passe como argumento"; exit 1; }
echo ">> target triple: $TRIPLE"

# --- venv de build isolado (não toca no .venv de dev, que pode ter o xtts) ---
BUILD_VENV=".venv-build"
uv venv "$BUILD_VENV" --python 3.12
uv pip install --python "$BUILD_VENV/bin/python" \
  "beautifulsoup4>=4.14.3" \
  "ebooklib>=0.20" \
  "fastapi>=0.136.3" \
  "piper-tts>=1.4.2" \
  "pypdf>=6.12.2" \
  "uvicorn[standard]>=0.48.0" \
  pyinstaller

# --- empacota ---
"$BUILD_VENV/bin/pyinstaller" --noconfirm --clean incipit-backend.spec

# --- instala no diretório de binaries do Tauri ---
DEST="../app/src-tauri/binaries"
mkdir -p "$DEST"
cp "dist/incipit-backend" "$DEST/incipit-backend-$TRIPLE"
chmod +x "$DEST/incipit-backend-$TRIPLE"
echo ">> sidecar instalado: $DEST/incipit-backend-$TRIPLE"
