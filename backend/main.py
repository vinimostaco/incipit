from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from incipit.api import router

app = FastAPI(title="incipit-backend")

# O webview do Tauri faz fetch cross-origin (dev: localhost:1420; build:
# tauri://localhost). Como o servidor só escuta em 127.0.0.1, liberar as
# origens é seguro e necessário para o preflight CORS passar.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
