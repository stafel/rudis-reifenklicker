"""Zugriff auf die 'Reifen-Datenbank' (PostgreSQL).

Die Datenbank ist der stateful Teil der Anwendung. Der Counter liegt
absichtlich in der Datenbank und nicht im Pod-Speicher, damit ein
Neustart oder Austausch eines Backend-Pods nichts verliert.
"""

import asyncio
import os

import asyncpg

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "reifenklicker")
DB_USER = os.getenv("DB_USER", "reifenklicker")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tire_counter (
    id         integer PRIMARY KEY,
    count      bigint NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO tire_counter (id, count) VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;
"""


async def create_pool(retries: int = 30, delay: float = 2.0) -> asyncpg.Pool:
    """Verbindet mit Retry, weil die Datenbank beim Start noch nicht bereit ist."""
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            pool = await asyncpg.create_pool(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                min_size=1,
                max_size=5,
            )
            async with pool.acquire() as conn:
                await conn.execute(SCHEMA)
            return pool
        except (OSError, asyncpg.PostgresError) as exc:
            last_error = exc
            print(f"[db] Verbindung fehlgeschlagen ({attempt}/{retries}): {exc}", flush=True)
            await asyncio.sleep(delay)
    raise RuntimeError(f"Konnte keine Verbindung zur Datenbank aufbauen: {last_error}")


async def get_count(pool: asyncpg.Pool) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT count FROM tire_counter WHERE id = 1")


async def increment(pool: asyncpg.Pool, delta: int) -> int:
    """Atomares Hochzählen, damit parallele Klicks nicht verloren gehen."""
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO tire_counter (id, count) VALUES (1, $1)
            ON CONFLICT (id) DO UPDATE
                SET count = tire_counter.count + EXCLUDED.count,
                    updated_at = now()
            RETURNING count
            """,
            delta,
        )


async def ping(pool: asyncpg.Pool) -> bool:
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return True
    except (OSError, asyncpg.PostgresError):
        return False
