"""AutoForge AI — Entry point."""

from fastapi import FastAPI

app = FastAPI(title="AutoForge AI", version="0.1.0")


@app.get("/health")
def health_check():
    return {"status": "ok"}
