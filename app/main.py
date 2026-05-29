from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.router import router
from app.tools.mock_db import init_db

app = FastAPI(title="Rappahannock Realty Group — Scout AI")

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

_frontend = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(_frontend)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(_frontend / "index.html"))


@app.get("/dashboard")
async def dashboard():
    return FileResponse(str(_frontend / "dashboard.html"))
