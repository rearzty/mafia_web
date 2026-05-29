import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect

from app.db.models import User
from app.core.dependencies import get_current_user, get_current_user_ws
from app.game.config import GameConfig, Phase
from app.game.dependencies import get_current_player, get_player_in_game, get_game
from app.game.core import Game
from app.game.phase import starting_phase
from app.game.storage import mafia_players, mafia_games
import uuid

from app.game.websocket import manager, handle_action, get_game_state
from app.schemas.game import GameResponse, GameStatusResponse

router = APIRouter()


@router.post("/create", response_model=GameResponse)
def create_game(_: User = Depends(get_current_player)):
    game_id = uuid.uuid4().__str__()
    mafia_games[game_id] = Game()
    return {'game_id': game_id}


@router.post("/{game_id}/join", response_model=GameResponse)
async def join_game(game_id: str = Depends(get_game), current_user: User = Depends(get_current_player)):
    mafia_games[game_id].player_join(current_user)
    mafia_players[current_user.id] = game_id
    await manager.broadcast(game_id, {
        "type": "player_joined",
    })
    return {'game_id': game_id}


@router.post("/{game_id}/leave", response_model=GameResponse)
async def leave_game(game_id: str = Depends(get_game), current_user: User = Depends(get_player_in_game)):
    mafia_games[game_id].player_leave(current_user)
    del mafia_players[current_user.id]
    await manager.broadcast(game_id, {
        "type": "player_left",
    })
    if not mafia_games[game_id].players:
        del mafia_games[game_id]

    return {'game_id': game_id}


@router.post("/{game_id}/start", response_model=GameResponse)
async def start_game(game_id: str = Depends(get_game), current_user: User = Depends(get_player_in_game)):
    if mafia_games[game_id].players[0] == current_user.id and mafia_games[game_id].start_game():
        game = mafia_games[game_id]
        asyncio.create_task(starting_phase(game_id, game))
        for player_id in game.players:
            await manager.send_to_player(game_id, player_id, {
                "type": "game_started",
                **get_game_state(game, player_id),
                "duration": GameConfig.STARTING_TIME
            })
        return {'game_id': game_id}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Game can be started only by creator and {GameConfig.MIN_PLAYERS}+ players")


@router.get("/{game_id}/status", response_model=GameStatusResponse)
def game_status(game_id: str, current_user: User = Depends(get_current_user)):
    game = mafia_games.get(game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if current_user.id not in game.players:
        raise HTTPException(403, "Not in game")

    return {
        "phase": game.phase.value,
        "players": [
            {
                "id": pid,
                "username": game.players_usernames[pid],
                "is_dead": pid in game.dead
            }
            for pid in game.players
        ],
        "my_role": game.players_roles.get(current_user.id).value if current_user.id in game.players_roles else None
    }


@router.websocket("/ws/{game_id}")
async def websocket_game(
        websocket: WebSocket,
        game_id: str,
        user: User = Depends(get_current_user_ws)
):
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
        manager.disconnect(game_id, user.id)
