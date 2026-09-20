"""Rudis Reifenklicker - Backend API.

Stateless FastAPI-Anwendung: Der gesamte Zustand (der montierte
Reifen-Counter) liegt in PostgreSQL. Jeder Pod ist austauschbar.
"""

import os
import random
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db

APP_VERSION = os.getenv("APP_VERSION", "v1")
CLICK_STEP = int(os.getenv("CLICK_STEP", "1"))
FEATURE_GOLDEN_RIM = os.getenv("FEATURE_GOLDEN_RIM", "false").lower() == "true"
GOLDEN_RIM_BONUS = int(os.getenv("GOLDEN_RIM_BONUS", "10"))
GOLDEN_RIM_CHANCE = float(os.getenv("GOLDEN_RIM_CHANCE", "0.1"))

POD_NAME = socket.gethostname()

SEASON_BY_VERSION = {"v1": "Sommerreifen-Edition", "v2": "Winterreifen-Edition"}

pool: db.asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global pool
    pool = await db.create_pool()
    print(f"[app] {APP_VERSION} bereit als {POD_NAME}", flush=True)
    yield
    if pool is not None:
        await pool.close()


app = FastAPI(title="Rudis Reifenklicker API", version=APP_VERSION, lifespan=lifespan)

# Fuer lokale Entwicklung (z.B. Frontend auf einem anderen Port).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _state(count: int) -> dict:
    return {
        "count": count,
        "version": APP_VERSION,
        "season": SEASON_BY_VERSION.get(APP_VERSION, "Entwicklungsstand"),
        "pod": POD_NAME,
        "goldenRim": FEATURE_GOLDEN_RIM,
    }


@app.get("/api/count")
async def read_count():
    return _state(await db.get_count(pool))


@app.post("/api/click")
async def click():
    delta = CLICK_STEP
    golden = False
    if FEATURE_GOLDEN_RIM and random.random() < GOLDEN_RIM_CHANCE:
        delta += GOLDEN_RIM_BONUS
        golden = True

    count = await db.increment(pool, delta)
    return {**_state(count), "delta": delta, "golden": golden}


@app.get("/api/version")
async def version():
    return {"version": APP_VERSION, "season": SEASON_BY_VERSION.get(APP_VERSION), "pod": POD_NAME}


@app.get("/api/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/api/readyz")
async def readyz():
    if pool is None or not await db.ping(pool):
        return JSONResponse(status_code=503, content={"status": "database not ready"})
    return {"status": "ready"}
