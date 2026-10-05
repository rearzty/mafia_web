from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.schemas.user import UserResponse
from app.core.dependencies import get_current_user
from app.game.storage import mafia_players, mafia_games


def get_current_player(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> UserResponse:
    if current_user.id in mafia_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Уже в игре"
        )
    return current_user


def get_game(game_id: str) -> str:
    if game_id not in mafia_games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Игра не найдена"
        )
    return game_id


def get_player_in_game(game_id: Annotated[str, Depends(get_game)],
                       current_user: Annotated[UserResponse, Depends(get_current_user)]) -> UserResponse:
    if not mafia_games[game_id].is_in_game(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Не является игроком"
        )
    return current_user
