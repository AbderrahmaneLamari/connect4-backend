from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import random
import math

app = FastAPI()

# Constants
ROW_COUNT = 6
COLUMN_COUNT = 7
WINDOW_LENGTH = 4
EMPTY = 0
PLAYER_PIECE = 1
AI_PIECE = 2

# In-memory game state
board = np.zeros((ROW_COUNT, COLUMN_COUNT))


class Move(BaseModel):
    column: int


def create_board():
    return np.zeros((ROW_COUNT, COLUMN_COUNT))


def drop_piece(board, row, col, piece):
    board[row][col] = piece


def is_valid_location(board, col):
    return board[ROW_COUNT - 1][col] == 0


def get_next_open_row(board, col):
    for r in range(ROW_COUNT):
        if board[r][col] == 0:
            return r


def winning_move(board, piece):
    for c in range(COLUMN_COUNT - 3):
        for r in range(ROW_COUNT):
            if all(board[r][c + i] == piece for i in range(4)):
                return True
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT - 3):
            if all(board[r + i][c] == piece for i in range(4)):
                return True
    for c in range(COLUMN_COUNT - 3):
        for r in range(ROW_COUNT - 3):
            if all(board[r + i][c + i] == piece for i in range(4)):
                return True
    for c in range(COLUMN_COUNT - 3):
        for r in range(3, ROW_COUNT):
            if all(board[r - i][c + i] == piece for i in range(4)):
                return True
    return False


def evaluate_window(window, piece):
    score = 0
    opp_piece = PLAYER_PIECE if piece == AI_PIECE else AI_PIECE

    if window.count(piece) == 4:
        score += 100
    elif window.count(piece) == 3 and window.count(EMPTY) == 1:
        score += 5
    elif window.count(piece) == 2 and window.count(EMPTY) == 2:
        score += 2

    if window.count(opp_piece) == 3 and window.count(EMPTY) == 1:
        score -= 4

    return score


def score_position(board, piece):
    score = 0
    center_array = [int(i) for i in list(board[:, COLUMN_COUNT // 2])]
    center_count = center_array.count(piece)
    score += center_count * 3

    for r in range(ROW_COUNT):
        row_array = [int(i) for i in list(board[r, :])]
        for c in range(COLUMN_COUNT - 3):
            window = row_array[c:c + WINDOW_LENGTH]
            score += evaluate_window(window, piece)

    for c in range(COLUMN_COUNT):
        col_array = [int(i) for i in list(board[:, c])]
        for r in range(ROW_COUNT - 3):
            window = col_array[r:r + WINDOW_LENGTH]
            score += evaluate_window(window, piece)

    for r in range(ROW_COUNT - 3):
        for c in range(COLUMN_COUNT - 3):
            window = [board[r + i][c + i] for i in range(WINDOW_LENGTH)]
            score += evaluate_window(window, piece)

    for r in range(ROW_COUNT - 3):
        for c in range(COLUMN_COUNT - 3):
            window = [board[r + 3 - i][c + i] for i in range(WINDOW_LENGTH)]
            score += evaluate_window(window, piece)

    return score


def is_terminal_node(board):
    return winning_move(board, PLAYER_PIECE) or winning_move(board, AI_PIECE) or len(get_valid_locations(board)) == 0


def get_valid_locations(board):
    return [c for c in range(COLUMN_COUNT) if is_valid_location(board, c)]


def minimax(board, depth, alpha, beta, maximizingPlayer):
    valid_locations = get_valid_locations(board)
    is_terminal = is_terminal_node(board)

    if depth == 0 or is_terminal:
        if is_terminal:
            if winning_move(board, AI_PIECE):
                return (None, 1e12)
            elif winning_move(board, PLAYER_PIECE):
                return (None, -1e12)
            else:
                return (None, 0)
        else:
            return (None, score_position(board, AI_PIECE))

    if maximizingPlayer:
        value = -math.inf
        column = random.choice(valid_locations)
        for col in valid_locations:
            row = get_next_open_row(board, col)
            b_copy = board.copy()
            drop_piece(b_copy, row, col, AI_PIECE)
            new_score = minimax(b_copy, depth - 1, alpha, beta, False)[1]
            if new_score > value:
                value = new_score
                column = col
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return column, value
    else:
        value = math.inf
        column = random.choice(valid_locations)
        for col in valid_locations:
            row = get_next_open_row(board, col)
            b_copy = board.copy()
            drop_piece(b_copy, row, col, PLAYER_PIECE)
            new_score = minimax(b_copy, depth - 1, alpha, beta, True)[1]
            if new_score < value:
                value = new_score
                column = col
            beta = min(beta, value)
            if alpha >= beta:
                break
        return column, value

@app.get("/")
def read_root():
    return "Hello there!"
@app.post("/new_game")
def new_game():
    global board
    board = create_board()
    return {"message": "New game started", "board": board.tolist()}


@app.post("/player_move")
def player_move(move: Move):
    global board
    if not is_valid_location(board, move.column):
        raise HTTPException(status_code=400, detail="Invalid player move")

    # Player move
    row = get_next_open_row(board, move.column)
    drop_piece(board, row, move.column, PLAYER_PIECE)
    player_wins = winning_move(board, PLAYER_PIECE)
    if player_wins:
        return {
            "board": board.tolist(),
            "player_wins": True,
            "ai_move": None,
            "ai_wins": False
        }

    # AI move
    col, _ = minimax(board, 4, -math.inf, math.inf, True)
    if col is None or not is_valid_location(board, col):
        return {
            "board": board.tolist(),
            "player_wins": False,
            "ai_move": None,
            "ai_wins": False,
            "message": "AI cannot make a move"
        }

    row = get_next_open_row(board, col)
    drop_piece(board, row, col, AI_PIECE)
    ai_wins = winning_move(board, AI_PIECE)

    return {
        "board": board.tolist(),
        "player_wins": False,
        "ai_move": col,
        "ai_wins": ai_wins
    }


@app.get("/ai_move")
def ai_move():
    global board
    col, _ = minimax(board, 4, -math.inf, math.inf, True)
    if col is None or not is_valid_location(board, col):
        raise HTTPException(status_code=400, detail="AI cannot make a move")
    row = get_next_open_row(board, col)
    drop_piece(board, row, col, AI_PIECE)
    return {
        "board": board.tolist(),
        "winner": winning_move(board, AI_PIECE)
    }
