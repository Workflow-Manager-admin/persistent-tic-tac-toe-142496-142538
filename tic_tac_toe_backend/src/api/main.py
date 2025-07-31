from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Path
from typing import List, Optional, Any

from . import models
from . import database
from . import core

app = FastAPI(
    title="Tic Tac Toe Game Backend",
    version="1.0.0",
    description="Backend API for Tic Tac Toe game with persistent PostgreSQL storage.",
    openapi_tags=[
        {"name": "Players", "description": "Player management."},
        {"name": "Games", "description": "Game creation, joining, and listing."},
        {"name": "Moves", "description": "Submitting moves and validating game logic."},
        {"name": "History", "description": "Game history/replay."}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health"], summary="Health Check", response_model=dict)
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


# -- PLAYERS --
@app.post("/players", tags=["Players"], response_model=models.PlayerOut, status_code=status.HTTP_201_CREATED)
async def api_create_player(player: models.PlayerCreate):
    # Unique usernames only
    exists = await database.get_player_by_username(player.username)
    if exists:
        raise HTTPException(status_code=409, detail="Username already taken")
    rec = await database.create_player(player.username)
    return models.PlayerOut(**rec)

@app.get("/players/{player_id}", tags=["Players"], response_model=models.PlayerOut)
async def api_get_player(player_id: int = Path(..., gt=0, description="Player id")):
    data = await database.get_player(player_id)
    if not data:
        raise HTTPException(status_code=404, detail="Player not found")
    return models.PlayerOut(**data)


# -- GAMES --
@app.post("/games", tags=["Games"], response_model=models.GameOut, status_code=status.HTTP_201_CREATED)
async def api_create_game(game_req: models.GameCreate):
    """Create a new game."""
    for pid in [game_req.player_x_id, game_req.player_o_id]:
        if pid and not await database.get_player(pid):
            raise HTTPException(status_code=404, detail=f"Player {pid} not found")
    g = await database.create_game(player_x_id=game_req.player_x_id, player_o_id=game_req.player_o_id)
    xinfo = await database.get_player(g["player_x_id"])
    oinfo = await database.get_player(g["player_o_id"]) if g["player_o_id"] else None
    return models.GameOut(
        id=g["id"],
        player_x=models.PlayerOut(**xinfo),
        player_o=models.PlayerOut(**oinfo) if oinfo else None,
        board=_deserialize_board(g["board"]),
        next_turn=g["next_turn"],
        winner=g["winner"],
        created_at=g["created_at"],
        finished_at=g["finished_at"]
    )

@app.post("/games/{game_id}/join", tags=["Games"], response_model=models.GameOut)
async def api_join_game(game_id: int, join_req: models.PlayerCreate):
    """Join an open game as Player O."""
    player = await database.get_player_by_username(join_req.username)
    if not player:
        player = await database.create_player(join_req.username)
    g = await database.join_game(game_id, player["id"])
    if not g:
        raise HTTPException(status_code=400, detail="Game already has two players or does not exist")
    xinfo = await database.get_player(g["player_x_id"])
    oinfo = await database.get_player(g["player_o_id"])
    return models.GameOut(
        id=g["id"],
        player_x=models.PlayerOut(**xinfo),
        player_o=models.PlayerOut(**oinfo),
        board=_deserialize_board(g["board"]),
        next_turn=g["next_turn"],
        winner=g["winner"],
        created_at=g["created_at"],
        finished_at=g["finished_at"]
    )

@app.get("/games", tags=["Games"], response_model=List[models.GameOut])
async def api_list_games(limit: int = 20):
    """List recent games."""
    out = []
    for g in await database.list_games(limit=limit):
        xinfo = await database.get_player(g["player_x_id"])
        oinfo = await database.get_player(g["player_o_id"]) if g["player_o_id"] else None
        out.append(models.GameOut(
            id=g["id"],
            player_x=models.PlayerOut(**xinfo),
            player_o=models.PlayerOut(**oinfo) if oinfo else None,
            board=_deserialize_board(g["board"]),
            next_turn=g["next_turn"],
            winner=g["winner"],
            created_at=g["created_at"],
            finished_at=g["finished_at"]
        ))
    return out

@app.get("/games/{game_id}", tags=["Games"], response_model=models.GameOut)
async def api_get_game(game_id: int):
    g = await database.get_game(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    xinfo = await database.get_player(g["player_x_id"])
    oinfo = await database.get_player(g["player_o_id"]) if g["player_o_id"] else None
    return models.GameOut(
        id=g["id"],
        player_x=models.PlayerOut(**xinfo),
        player_o=models.PlayerOut(**oinfo) if oinfo else None,
        board=_deserialize_board(g["board"]),
        next_turn=g["next_turn"],
        winner=g["winner"],
        created_at=g["created_at"],
        finished_at=g["finished_at"]
    )

# -- MOVES --
@app.post("/games/{game_id}/moves", tags=["Moves"], response_model=models.MoveOut)
async def api_submit_move(game_id: int, move: models.MoveCreate):
    """
    Submit a move. Checks validity, update game, stores move, returns new game state.
    """
    g = await database.get_game(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    # Security: Check player belongs to this game
    if move.player_id not in [g["player_x_id"], g.get("player_o_id")]:
        raise HTTPException(status_code=403, detail="Player not part of this game")
    board = _deserialize_board(g["board"])
    player_symbol = 'X' if move.player_id == g["player_x_id"] else 'O'
    # Winner/final: prevent moves
    if g["winner"]:
        raise HTTPException(status_code=400, detail="Game already finished")
    # Whose turn?
    if g["next_turn"] != player_symbol:
        raise HTTPException(status_code=403, detail="Not your turn")
    if not core.is_valid_move(board, move.x, move.y):
        raise HTTPException(status_code=400, detail="Invalid move")
    # Apply move
    board = core.make_move(board, move.x, move.y, player_symbol)
    winner = core.check_win(board)
    draw = core.check_draw(board)
    finished = (winner is not None) or draw
    next_t = None if finished else core.next_turn(g["next_turn"])
    winner_str = winner or ("Draw" if draw else None)
    await database.update_game_board(game_id, board, next_t, winner_str)
    if finished and winner_str:
        await database.finish_game(game_id, winner_str)
    mov = await database.add_move(game_id, move.player_id, move.x, move.y, player_symbol)
    player_obj = await database.get_player(move.player_id)
    return models.MoveOut(
        id=mov["id"],
        game_id=game_id,
        player=models.PlayerOut(**player_obj),
        x=mov["x"],
        y=mov["y"],
        symbol=mov["symbol"],
        timestamp=mov["timestamp"]
    )

# -- HISTORY --
@app.get("/games/{game_id}/history", tags=["History"], response_model=models.GameHistoryOut)
async def api_game_history(game_id: int):
    g = await database.get_game(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    moves = await database.get_moves_for_game(game_id)
    xinfo = await database.get_player(g["player_x_id"])
    oinfo = await database.get_player(g["player_o_id"]) if g["player_o_id"] else None
    moves_out = [
        models.MoveOut(
            id=m["id"], game_id=game_id,
            player=models.PlayerOut(id=m["player_id"], username=m["username"]),
            x=m["x"], y=m["y"], symbol=m["symbol"], timestamp=m["timestamp"]
        ) for m in moves
    ]
    return models.GameHistoryOut(
        game=models.GameOut(
            id=g["id"],
            player_x=models.PlayerOut(**xinfo),
            player_o=models.PlayerOut(**oinfo) if oinfo else None,
            board=_deserialize_board(g["board"]),
            next_turn=g["next_turn"],
            winner=g["winner"],
            created_at=g["created_at"],
            finished_at=g["finished_at"]
        ),
        moves=moves_out
    )

# UTILS
def _deserialize_board(board: Any) -> List[List[Optional[str]]]:
    """Convert board from string/JSON serialization to python object."""
    if isinstance(board, str):
        import json
        return json.loads(board)
    return board
