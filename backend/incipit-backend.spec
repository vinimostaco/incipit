# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller para o sidecar do incipit (onefile).

Empacota SÓ o backend leve: extração (PDF/EPUB) + TTS Piper. O XTTS (PyTorch)
fica de fora de propósito — é caminho opcional/futuro, manteria o binário gigante.
Por isso torch/TTS/transformers entram em `excludes`: mesmo que o código tenha
import preguiçoso do XTTS, ele nunca é empacotado.

Data files que importam:
  - piper/espeak-ng-data/* e piper/espeakbridge.so  (fonemização)
  - onnxruntime (libs nativas)  -> via collect_all
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

for pkg in ("piper", "onnxruntime"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# uvicorn[standard] importa loops/protocolos dinamicamente (uvloop, httptools, ...).
hiddenimports += collect_submodules("uvicorn")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "torch",
        "torchaudio",
        "TTS",
        "transformers",
        "scipy",
        "pandas",
        "matplotlib",
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="incipit-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
