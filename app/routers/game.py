import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect

from app.schemas.user import UserResponse
from app.core.dependencies import get_current_user_ws
from app.game.config import GameConfig, Phase
from app.game.dependencies import get_current_player, get_player_in_game, get_game
from app.game.core import Game
from app.game.phase import starting_phase
from app.game.storage import mafia_players, mafia_games
import uuid

from app.game.websocket import manager, handle_action, get_game_state
from app.schemas.game import GameResponse, GameStatusResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create", response_model=GameResponse)
async def create_game(current_user: Annotated[UserResponse, Depends(get_current_player)]):
    game_id = uuid.uuid4().__str__()
    game = Game()
    game.player_join(current_user)
    mafia_games[game_id] = game
    mafia_players[current_user.id] = game_id
    return {'game_id': game_id}


@router.post("/{game_id}/join", response_model=GameResponse)
async def join_game(game_id: Annotated[str, Depends(get_game)],
                    current_user: Annotated[UserResponse, Depends(get_current_player)]):
    game = mafia_games[game_id]
    async with game.lock:
        if current_user.id in mafia_players:
            raise HTTPException(status_code=400, detail="Уже в игре")
        if game.phase != Phase.WAITING:
            raise HTTPException(status_code=400, detail="Игра уже началась")
        if len(game.players) >= GameConfig.MAX_PLAYERS:
            raise HTTPException(status_code=400, detail="Достигнуто максимальное количество игроков")
        game.player_join(current_user)
        mafia_players[current_user.id] = game_id
    await manager.broadcast(game_id, {
        "type": "player_joined",
    })
    return {'game_id': game_id}


@router.post("/{game_id}/leave", response_model=GameResponse)
async def leave_game(game_id: Annotated[str, Depends(get_game)],
                     current_user: Annotated[UserResponse, Depends(get_player_in_game)]):
    game = mafia_games[game_id]
    async with game.lock:
        game.player_leave(current_user)
        mafia_players.pop(current_user.id, None)
        if game.is_empty():
            del mafia_games[game_id]

    await manager.broadcast(game_id, {
        "type": "player_left",
    })

    return {'game_id': game_id}


@router.post("/{game_id}/start", response_model=GameResponse)
async def start_game(game_id: Annotated[str, Depends(get_game)],
                     current_user: Annotated[UserResponse, Depends(get_player_in_game)]):
    game = mafia_games[game_id]
    async with game.lock:
        can_start = game.players and game.players[0] == current_user.id and game.start_game()

    if can_start:
        asyncio.create_task(starting_phase(game_id, game))
        for player_id in game.players:
            await manager.send_to_player(game_id, player_id, {
                "type": "game_started",
                **get_game_state(game, player_id),
                "duration": GameConfig.STARTING_TIME
            })
        return {'game_id': game_id}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Игра может быть запущена только создателем и когда в игре больше {GameConfig.MIN_PLAYERS} игроков")


@router.get("/{game_id}/status", response_model=GameStatusResponse)
def game_status(game_id: Annotated[str, Depends(get_game)],
                current_user: Annotated[UserResponse, Depends(get_player_in_game)]):
    return get_game_state(mafia_games[game_id], current_user.id)


@router.websocket("/ws/{game_id}")
async def websocket_game(
        websocket: WebSocket,
        game_id: str,
        user: Annotated[UserResponse, Depends(get_current_user_ws)]
):
    if not user:
        return

    game = mafia_games.get(game_id)
    if not game:
        await websocket.close(code=4002, reason="Игра не найдена")
        return

    if not game.is_in_game(user.id):
        await websocket.close(code=4003, reason="Вы не в этой игре")
        return

    await manager.connect(game_id, user.id, websocket)
    try:
        await manager.send_to_player(game_id, user.id, {
            "type": "connected",
            **get_game_state(game, user.id)
        })

        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue

            action = data.get("action")
            target_id = data.get("target_id")
            message = data.get("message")

            result = await handle_action(
                game=game,
                player_id=user.id,
                action=action,
                target_id=target_id,
                game_id=game_id,
                message=message
            )

            await manager.send_to_player(game_id, user.id, {
                "type": "action_result",
                **result
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Ошибка websocket игрока {user.id} в {game_id}: {e}")
    finally:
        manager.disconnect(game_id, user.id, websocket)
