from fastapi import WebSocket
from typing import Dict

from app.game.config import Action
from app.game.core import Game, Phase, Role


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[int, WebSocket]] = {}

    async def connect(self, game_id: str, player_id: int, websocket: WebSocket):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
        self.active_connections[game_id][player_id] = websocket

    def disconnect(self, game_id: str, player_id: int):
        if game_id in self.active_connections:
            self.active_connections[game_id].pop(player_id, None)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def send_to_player(self, game_id: str, player_id: int, message: dict):
        if game_id in self.active_connections:
            ws = self.active_connections[game_id].get(player_id)
            if ws:
                await ws.send_json(message)

    async def broadcast(self, game_id: str, message: dict, exclude: list[int] = None):
        if game_id in self.active_connections:
            exclude = exclude or []
            for player_id, ws in self.active_connections[game_id].items():
                if player_id not in exclude:
                    await ws.send_json(message)


manager = ConnectionManager()


async def handle_action(game: Game, player_id: int, action: str, target_id: int, game_id: str, message: str):
    if action == "chat":
        if game.phase in [Phase.NIGHT, Phase.VOTING]:
            return {"success": False, "message": "Chat disabled in this phase"}
        if message and len(message) <= 200:
            await manager.broadcast(game_id, {
                "type": "chat",
                "username": game.players_usernames[player_id],
                "message": message
            })
            return {"success": True, "message": "Sent"}
        return {"success": False, "message": "Invalid message"}
    if game.action_used.get(player_id):
        return {"success": False, "message": "Вы уже сделали выбор"}
    game.action_used[player_id] = True
    if action == Action.MAFIA_KILL.value:
        if game.phase != Phase.NIGHT:
            return {"success": False, "message": "Сейчас не ночь"}
        if game.players_roles.get(player_id) != Role.MAFIA:
            return {"success": False, "message": "Вы не мафия"}
        if player_id in game.dead:
            return {"success": False, "message": "Вы мертвы"}

        game.mafia_kill(target_id)
        return {"success": True, "message": "Голос принят"}

    elif action == Action.HEAL.value:
        if game.phase != Phase.NIGHT:
            return {"success": False, "message": "Сейчас не ночь"}
        if game.players_roles.get(player_id) != Role.DOCTOR:
            return {"success": False, "message": "Вы не доктор"}

        game.heal_player(target_id, player_id)
        return {"success": True, "message": "Выбор сделан"}

    elif action == Action.COMMISSIONER_KILL.value:
        if game.phase != Phase.NIGHT:
            return {"success": False, "message": "Сейчас не ночь"}
        if game.players_roles.get(player_id) != Role.COMMISSIONER:
            return {"success": False, "message": "Вы не комиссар"}
        if game.COMMISSIONER_kill_used:
            return {"success": False, "message": "Вы уже использовали убийство"}

        game.commissioner_kill(target_id)
        return {"success": True, "message": "Выбор сделан"}
    elif action == Action.COMMISSIONER_CHECK.value:
        if game.phase != Phase.NIGHT:
            return {"success": False, "message": "Сейчас не ночь"}
        if game.players_roles.get(player_id) != Role.COMMISSIONER:
            return {"success": False, "message": "Вы не комиссар"}

        result = game.commissioner_check(target_id)
        return {"success": True, "message": f"Выбранный игрок - {result}"}

    elif action == Action.VOTE.value:
        if game.phase != Phase.VOTING:
            return {"success": False, "message": "Not voting phase"}
        if player_id in game.dead:
            return {"success": False, "message": "Dead players cannot vote"}

        game.voting[player_id] = target_id
        return {"success": True, "message": "Vote registered"}

    return {"success": False, "message": "Unknown action"}


def get_game_state(game: Game, player_id: int) -> dict:
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
        "my_role": game.players_roles.get(player_id).value if player_id in game.players_roles else None,
        "has_acted": game.action_used.get(player_id, False)
    }
