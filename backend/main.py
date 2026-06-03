from fastapi import FastAPI

from incipit.api import router

app = FastAPI(title="incipit-backend")
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
