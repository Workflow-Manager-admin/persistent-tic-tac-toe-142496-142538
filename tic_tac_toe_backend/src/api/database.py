import os
import asyncpg
from typing import List, Optional, Any, Dict
from contextlib import asynccontextmanager

DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("POSTGRES_URL")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

DSN = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

_pool: Optional[asyncpg.pool.Pool] = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=DSN, min_size=1, max_size=10)
    return _pool

@asynccontextmanager
async def connect():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn

# --- PLAYER ---
async def create_player(username: str) -> Dict[str, Any]:
    async with connect() as conn:
        row = await conn.fetchrow("INSERT INTO player (username) VALUES ($1) RETURNING id, username", username)
        return dict(row)

async def get_player(player_id: int) -> Optional[Dict[str, Any]]:
    async with connect() as conn:
        row = await conn.fetchrow("SELECT id, username FROM player WHERE id = $1", player_id)
        return dict(row) if row else None

async def get_player_by_username(username: str) -> Optional[Dict[str, Any]]:
    async with connect() as conn:
        row = await conn.fetchrow("SELECT id, username FROM player WHERE username = $1", username)
        return dict(row) if row else None

# --- GAME ---
async def create_game(player_x_id: int, player_o_id: Optional[int]=None) -> Dict[str, Any]:
    async with connect() as conn:
        row = await conn.fetchrow(
            """INSERT INTO game (player_x_id, player_o_id, next_turn, board, created_at)
            VALUES ($1, $2, 'X', '[["", "", ""], ["", "", ""], ["", "", ""]]', NOW())
            RETURNING *""", player_x_id, player_o_id)
        return dict(row)

async def join_game(game_id: int, player_o_id: int) -> Optional[Dict[str, Any]]:
    async with connect() as conn:
        row = await conn.fetchrow(
            "UPDATE game SET player_o_id = $1 WHERE id = $2 AND player_o_id IS NULL RETURNING *",
            player_o_id, game_id)
        return dict(row) if row else None

async def get_game(game_id: int) -> Optional[Dict[str, Any]]:
    async with connect() as conn:
        row = await conn.fetchrow("SELECT * FROM game WHERE id=$1", game_id)
        return dict(row) if row else None

async def list_games(limit=20) -> List[Dict[str, Any]]:
    async with connect() as conn:
        rows = await conn.fetch(
            "SELECT * FROM game ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(row) for row in rows]

async def finish_game(game_id: int, winner: Optional[str]) -> None:
    async with connect() as conn:
        await conn.execute(
            "UPDATE game SET winner=$1, finished_at=NOW() WHERE id=$2", winner, game_id
        )

async def update_game_board(game_id: int, board: List[List[str]], next_turn: Optional[str], winner: Optional[str]) -> None:
    async with connect() as conn:
        await conn.execute(
            "UPDATE game SET board=$1, next_turn=$2, winner=$3 WHERE id=$4",
            board, next_turn, winner, game_id
        )

# --- MOVES ---
async def add_move(game_id: int, player_id: int, x: int, y: int, symbol: str) -> Dict[str, Any]:
    async with connect() as conn:
        row = await conn.fetchrow(
            """INSERT INTO move (game_id, player_id, x, y, symbol, timestamp)
               VALUES ($1, $2, $3, $4, $5, NOW())
               RETURNING *""",
            game_id, player_id, x, y, symbol)
        return dict(row)

async def get_moves_for_game(game_id: int) -> List[Dict[str, Any]]:
    async with connect() as conn:
        rows = await conn.fetch(
            """SELECT m.*, p.username
               FROM move m
               JOIN player p ON m.player_id=p.id
               WHERE game_id=$1 ORDER BY timestamp ASC""", game_id)
        return [dict(row) for row in rows]
