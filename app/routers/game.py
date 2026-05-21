import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect

from app.db.database import SessionLocal
from app.db.models import User
from app.dependencies import get_current_user
from app.game.config import GameConfig, Phase
from app.game.dependencies import get_current_player, get_player_in_game, get_game
from app.game.core import Game
from app.game.phase import starting_phase
from app.game.storage import mafia_players, mafia_games
import uuid

from app.game.websocket import manager, handle_action, get_game_state

router = APIRouter()


@router.post("/create")
def create_game(current_user: User = Depends(get_current_player)):
    game_id = str(uuid.uuid4())
    mafia_games[game_id] = Game()
    mafia_games[game_id].player_join(current_user)
    mafia_players[current_user.id] = game_id
    return {'game_id': game_id}


@router.post("/{game_id}/join")
def join_game(game_id: str = Depends(get_game), current_user: User = Depends(get_current_player)):
    mafia_games[game_id].player_join(current_user)
    return {'game_id': game_id}


@router.post("/{game_id}/leave")
def leave_game(game_id: str = Depends(get_game), current_user: User = Depends(get_player_in_game)):
    mafia_games[game_id].player_leave(current_user)
    return {'game_id': game_id}


@router.post("/{game_id}/start")
def start_game(game_id: str = Depends(get_game), current_user: User = Depends(get_player_in_game)):
    if mafia_games[game_id].players[0] == current_user.id and mafia_games[game_id].start_game():
        game = mafia_games[game_id]
        game.phase = Phase.STARTING
        asyncio.create_task(starting_phase(game_id, game))
        return {'game_id': game_id}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Game can be started only by creator and {GameConfig.MIN_PLAYERS}+ players")


@router.websocket("/ws/{game_id}")
async def websocket_game(
        websocket: WebSocket,
        game_id: str,
        token: str,
):
    db = SessionLocal()
    user = get_current_user(token, db)
    try:
        if not user:
            await websocket.close(code=4001, reason="Invalid token")
            return

        game = mafia_games.get(game_id)
        if not game:
            await websocket.close(code=4002, reason="Game not found")
            return

        if user.id not in game.players:
            await websocket.close(code=4003, reason="You are not in this game")
            return

        await manager.connect(game_id, user.id, websocket)

        await manager.send_to_player(game_id, user.id, {
            "type": "connected",
            **get_game_state(game, user.id)
        })

        while True:
            data = await websocket.receive_json()

            action = data.get("action")
            target_id = data.get("target_id")

            result = await handle_action(
                game=game,
                player_id=user.id,
                action=action,
                target_id=target_id,
                game_id=game_id
            )

            await manager.send_to_player(game_id, user.id, {
                "type": "action_result",
                **result
            })

    except WebSocketDisconnect:
        manager.disconnect(game_id, user.id)
    finally:
        db.close()
