from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

# PUBLIC_INTERFACE
class PlayerCreate(BaseModel):
    """Model for creating a new player."""
    username: str = Field(..., description="The player's username")

# PUBLIC_INTERFACE
class PlayerOut(BaseModel):
    """Model for serialized player info output."""
    id: int
    username: str

# PUBLIC_INTERFACE
class GameCreate(BaseModel):
    """Request body for creating a new game."""
    player_x_id: int = Field(..., description="Player X user id")
    player_o_id: Optional[int] = Field(None, description="Player O (can be null for waiting)")

# PUBLIC_INTERFACE
class GameOut(BaseModel):
    """Serialized game state for API output."""
    id: int
    player_x: PlayerOut
    player_o: Optional[PlayerOut]
    board: List[List[Optional[Literal['X', 'O']]]]
    next_turn: Optional[Literal['X', 'O']]
    winner: Optional[Literal['X', 'O', 'Draw']]
    created_at: datetime
    finished_at: Optional[datetime]

# PUBLIC_INTERFACE
class MoveCreate(BaseModel):
    """Request body for submitting a move."""
    player_id: int = Field(..., description="The player's id")
    x: int = Field(..., description="Row (0-2)")
    y: int = Field(..., description="Column (0-2)")

# PUBLIC_INTERFACE
class MoveOut(BaseModel):
    """Move output serialization."""
    id: int
    game_id: int
    player: PlayerOut
    x: int
    y: int
    symbol: Literal['X', 'O']
    timestamp: datetime

# PUBLIC_INTERFACE
class GameHistoryOut(BaseModel):
    """Serialized history for a game."""
    game: GameOut
    moves: List[MoveOut]
