"""Entry point: `uvicorn main:app --reload --port 8787` from web/backend."""

from app.factory import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8787, reload=True)
