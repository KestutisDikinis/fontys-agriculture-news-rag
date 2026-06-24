from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import settings

settings.ensure_dirs()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

UI_DIR = Path(__file__).resolve().parent / "ui"
if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")
