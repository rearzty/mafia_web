from fastapi import Depends, HTTPException, status

from app.db.models import User
from app.dependencies import get_current_user
from app.game.core import Game
from app.game.storage import mafia_players, mafia_games


def get_current_player(current_user: User = Depends(get_current_user)) -> User:
    if current_user.id in mafia_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already in a game"
        )
    return current_user


def get_game(game_id: str) -> Game:
    if game_id not in mafia_games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    return mafia_games[game_id]


def get_player_in_game(game_id: str = Depends(get_game), current_user: User = Depends(get_current_user)):
    if current_user.id not in mafia_games[game_id].players:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a game member"
        )
    return current_user