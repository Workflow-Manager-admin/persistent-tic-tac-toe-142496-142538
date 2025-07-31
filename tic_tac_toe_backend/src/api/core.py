from typing import List, Optional, Literal

PlayerSymbol = Literal['X', 'O']

def empty_board() -> List[List[Optional[PlayerSymbol]]]:
    return [[None for _ in range(3)] for _ in range(3)]

# PUBLIC_INTERFACE
def is_valid_move(board: List[List[Optional[PlayerSymbol]]], x: int, y: int) -> bool:
    """Check if a move is valid (cell is empty and indices are within range)."""
    return 0 <= x < 3 and 0 <= y < 3 and (board[x][y] is None or board[x][y] == '')

# PUBLIC_INTERFACE
def make_move(board: List[List[Optional[PlayerSymbol]]], x: int, y: int, symbol: PlayerSymbol) -> List[List[Optional[PlayerSymbol]]]:
    """Return a new board with the move applied."""
    new_board = [row[:] for row in board]
    new_board[x][y] = symbol
    return new_board

# PUBLIC_INTERFACE
def check_win(board: List[List[Optional[PlayerSymbol]]]) -> Optional[PlayerSymbol]:
    """Check if anyone has won: returns 'X', 'O', or None."""
    lines = []
    # Rows/Cols
    for i in range(3):
        lines.append(board[i])  # rows
        lines.append([board[0][i], board[1][i], board[2][i]])  # cols
    # Diagonals
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])
    for line in lines:
        if line[0] and line[0] == line[1] == line[2]:
            return line[0]
    return None

# PUBLIC_INTERFACE
def check_draw(board: List[List[Optional[PlayerSymbol]]]) -> bool:
    """Check if the board is full and there is no winner."""
    for row in board:
        if any(cell is None or cell == '' for cell in row):
            return False
    return check_win(board) is None

# PUBLIC_INTERFACE
def next_turn(current_turn: PlayerSymbol) -> PlayerSymbol:
    """Toggle turn: X -> O, O -> X."""
    return 'O' if current_turn == 'X' else 'X'
