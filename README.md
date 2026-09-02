# incipit

Leitor de texto por voz — app desktop que recebe PDFs, EPUBs e textos e os lê em voz alta.

> *incipit* (latim, "começa aqui") — a primeira linha de um manuscrito.

## Motivação

Projeto pessoal de acessibilidade, para uso prolongado e confortável de livros e textos por áudio.

## Arquitetura em uma tela

São **dois processos**, e eles não se falam por IPC do Tauri:

```
app/  (Tauri 2 + React 19 + TS)          backend/  (FastAPI, Python 3.12)
  src-tauri/src/lib.rs  ── spawn ──►  incipit-backend  (sidecar, externalBin)
  src/api.ts            ── fetch ──►  http://127.0.0.1:8765
                                        /health  /extract  /tts  /tts/engines
                                        /tts/pregenerate  (POST/GET/DELETE)
```

Consequência prática: a maior parte dos bugs de integração é **contrato HTTP**
entre dois runtimes, não fronteira de componente React nem de módulo Rust. É
por isso que `backend/tests/test_api_contract.py` é o teste mais importante do
repositório.

## Pré-requisitos

| O quê | Para quê | Verificado nesta linha de base |
|---|---|---|
| **Node ≥ 20** + npm | frontend (Vite/TS) | ✅ Node v22.20.0, npm 10.9.3 |
| **[uv](https://docs.astral.sh/uv/)** | backend; ele mesmo baixa o Python 3.12 | ✅ uv 0.12.9 → CPython 3.12.14 |
| **Rust estável** (via [rustup](https://rustup.rs/)) | compilar o app Tauri | ❌ ausente nesta máquina |
| **Libs de sistema do Tauri** (GTK/WebKit) | compilar e abrir a janela | ❌ ausentes nesta máquina |

Você **não** precisa instalar Python à mão: `uv` provisiona o 3.12 sozinho a
partir de `backend/.python-version`.

```bash
# uv (instala em ~/.local/bin)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Libs de sistema do Tauri (Debian/Ubuntu; exige root)
sudo apt update && sudo apt install -y \
  libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev \
  libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

Para conferir se as libs de sistema estão no lugar antes de gastar um `cargo build`:

```bash
pkg-config --exists webkit2gtk-4.1 && echo ok || echo "faltando"
```

## Rodando do zero

### 1. Backend em modo dev

```bash
cd backend
uv sync                                   # cria .venv e instala as dependências
uv run uvicorn main:app --port 8765
```

Em outro terminal:

```bash
curl localhost:8765/health                # {"status":"ok"}
curl localhost:8765/tts/engines           # {"engines":["piper","xtts"]}
```

A primeira chamada a `/tts` baixa a voz Piper (`pt_BR-faber-medium`, ~60 MB) sob
demanda, para `$INCIPIT_DATA_DIR` (padrão `~/.local/share/incipit`) — conte
alguns segundos a mais só nessa primeira vez.

### 2. Frontend

```bash
cd app
npm ci                                    # prefira `ci` a `install` — veja a nota abaixo
npm run build                             # tsc && vite build -> app/dist
```

### 3. App desktop (Tauri)

O sidecar tem de existir **antes** do build do Tauri: `tauri.conf.json` declara
`"externalBin": ["binaries/incipit-backend"]`, e o Tauri resolve esse caminho em
tempo de build, com o *target triple* no nome do arquivo.

```bash
cd backend && ./build_sidecar.sh          # uv + PyInstaller -> app/src-tauri/binaries/
cd ../app && npm run tauri dev            # janela do incipit, com o backend embutido
# empacotar: npm run tauri build
```

> **Mudou algo em `backend/incipit/`?** Não aparece no app empacotado até
> `build_sidecar.sh` rodar de novo. Enquanto estiver iterando no backend, rode-o
> solto (passo 1) — o `npm run tauri dev` conversa com a mesma porta 8765.

## Testes

```bash
cd backend
uv run pytest                             # suíte inteira
uv run pytest tests/test_api_contract.py  # só o contrato HTTP
```

Nenhum teste sintetiza áudio de verdade nem baixa modelo: os engines são
substituídos por dublês, e `tests/conftest.py` aponta `INCIPIT_DATA_DIR` para um
diretório temporário. A suíte roda em ~1s e não toca em `~/.local/share/incipit`.

### Goldens de extração

`tests/golden/*.json` congela o `Book` que cada fixture de `tests/fixtures/`
produz. Eles registram o comportamento **atual** de `extract.py` — verrugas
incluídas (veja o docstring de `test_extract_golden.py`) — e servem para
detectar mudança não intencional, inclusive vinda de bump de dependência. Os
goldens valem para as versões travadas em `uv.lock`.

Depois de decidir que uma mudança de comportamento é desejada:

```bash
uv run pytest tests/test_extract_golden.py --update-goldens
```

Os fixtures são gerados por `tests/fixtures/make_fixtures.py` (texto original,
livre de direitos; rode à mão só se quiser recriá-los).

## Linha de base verificada

Executado neste checkout, em Linux (WSL2), em 2026-09-02:

| Comando | Resultado |
|---|---|
| `uv sync` | ✅ 39 pacotes (com o grupo `dev`), CPython 3.12.14 |
| `uv run uvicorn main:app --port 8765` + `curl /health` | ✅ `{"status":"ok"}` |
| `curl -X POST /extract` (PDF de fixture) | ✅ 3 capítulos, 6 parágrafos |
| `curl -X POST /tts` (Piper real) | ✅ WAV mono 16-bit 22050 Hz, 3,01 s; `X-Cache: miss` → `hit` |
| `POST/GET /tts/pregenerate` | ✅ job `done` 3/3, cache preenchido |
| `npm ci && npm run build` em `app/` | ✅ `app/dist` gerado (tsc + vite) |
| `uv run pytest` | ✅ 55 passed |
| `npm run tauri dev` | ⛔ **não executado** — sem Rust e sem GTK/WebKit nesta máquina |

O passo 3 (janela aberta) é o único que continua **não verificado**. Ele depende
de `sudo apt install` das libs de sistema, que esta máquina não permite.

### Duas pegadinhas encontradas ao levantar a linha de base

- **`npm install` reescreve o lockfile.** O `package-lock.json` foi escrito por
  um npm mais novo, que registra campos `libc` nos pacotes opcionais de
  plataforma; o npm 10.9.3 os remove ao rodar `npm install`, sujando o diff.
  Use `npm ci`, que instala sem tocar no lockfile.
- **`npm audit` acusa 4 vulnerabilidades** (3 high) em dependências transitivas
  de desenvolvimento: `browserslist`, `esbuild`, `nanoid`, `postcss`. Nenhuma
  delas vai para o bundle do desktop. Ficam registradas aqui como estado da
  linha de base — corrigi-las é uma mudança de dependência, não parte deste
  levantamento.

## Stack

- **Frontend:** [Tauri 2](https://tauri.app/) + React 19 + TypeScript (Vite)
- **Backend:** FastAPI / Python 3.12, empacotado como sidecar por PyInstaller
- **Extração:** pypdf (PDF), ebooklib + BeautifulSoup (EPUB)
- **TTS:** Piper (offline, rápido em CPU — padrão) e Coqui XTTS v2
  (`uv sync --extra xtts`, traz PyTorch; qualidade máxima, lento em CPU)

## Status

Em desenvolvimento inicial.
