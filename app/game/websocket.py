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


async def handle_action(game: Game, player_id: int, action: str, target_id: int, game_id: str):
    if action == Action.MAFIA_KILL:
        if game.phase != Phase.NIGHT:
            return {"success": False, "message": "Not night phase"}
        if game.players_roles.get(player_id) != Role.MAFIA:
            return {"success": False, "message": "You are not mafia"}
        if player_id in game.dead:
            return {"success": False, "message": "You are dead"}

        game.mafia_kill(target_id)
        await manager.broadcast(game_id, {
            "type": "action_notify",
            "action": action.value,
            "player_id": player_id,
            "target_id": target_id
        }, exclude=[player_id])
        return {"success": True, "message": "Vote registered"}

    elif action == Action.HEAL:
        if game.phase != Phase.NIGHT:
            return {"success": False, "message": "Not night phase"}
        if game.players_roles.get(player_id) != Role.DOCTOR:
            return {"success": False, "message": "You are not doctor"}

        game.heal_player(target_id, player_id)
        return {"success": True, "message": "Heal registered"}

    elif action == Action.COMMISSIONER_KILL:
        if game.phase != Phase.NIGHT:
            return {"success": False, "message": "Not night phase"}
        if game.players_roles.get(player_id) != Role.COMMISSIONER:
            return {"success": False, "message": "You are not commissioner"}
        if game.COMMISSIONER_kill_used:
            return {"success": False, "message": "You already used your kill"}

        game.commissioner_kill(target_id)
        return {"success": True, "message": "Kill registered"}

    elif action == Action.VOTE:
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
        "my_role": game.players_roles.get(player_id) if player_id in game.players_roles else None,
        "alive_count": len([p for p in game.players if p not in game.dead]),
        "dead_count": len(game.dead)
    }
