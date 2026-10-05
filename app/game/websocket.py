import logging

from fastapi import WebSocket
from typing import Dict

from app.game.config import Action
from app.game.core import Game, Phase, Role

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[int, WebSocket]] = {}

    async def connect(self, game_id: str, player_id: int, websocket: WebSocket):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
        self.active_connections[game_id][player_id] = websocket

    def disconnect(self, game_id: str, player_id: int, websocket: WebSocket | None = None):
        if game_id in self.active_connections:
            connections = self.active_connections[game_id]
            if websocket is not None and connections.get(player_id) is not websocket:
                return
            connections.pop(player_id, None)
            if not connections:
                del self.active_connections[game_id]

    def is_connected(self, game_id: str, player_id: int) -> bool:
        return player_id in self.active_connections.get(game_id, {})

    async def send_to_player(self, game_id: str, player_id: int, message: dict):
        if game_id in self.active_connections:
            ws = self.active_connections[game_id].get(player_id)
            if ws:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение игроку {player_id} в {game_id}: {e}")
                    self.disconnect(game_id, player_id, ws)

    async def broadcast(self, game_id: str, message: dict, exclude: list[int] | None = None):
        if game_id in self.active_connections:
            exclude = exclude or []
            dead_players = []
            for player_id, ws in list(self.active_connections[game_id].items()):
                if player_id not in exclude:
                    try:
                        await ws.send_json(message)
                    except Exception as e:
                        logger.warning(f"Не удалось отправить сообщение игроку {player_id} в {game_id}: {e}")
                        dead_players.append((player_id, ws))
            for player_id, ws in dead_players:
                self.disconnect(game_id, player_id, ws)


manager = ConnectionManager()


async def handle_action(game: Game, player_id: int, action: str, target_id: int, game_id: str, message: str):
    async with game.lock:

        if action == "chat":
            if game.phase in [Phase.NIGHT, Phase.VOTING]:
                return {"success": False, "message": "Чат отключен"}
            if player_id in game.dead:
                return {"success": False, "message": "Мертвые не могут писать в чат"}
            if isinstance(message, str) and message and len(message) <= 200:
                await manager.broadcast(game_id, {
                    "type": "chat",
                    "username": game.players_usernames[player_id],
                    "message": message
                })
                return {"success": True, "message": "Sent"}
            return {"success": False, "message": "Некорректное сообщение"}
        if type(target_id) is not int or target_id not in game.players:
            return {"success": False, "message": "Некорректная цель"}
        if player_id in game.dead:
            return {"success": False, "message": "Вы мертвы"}
        if target_id in game.dead:
            return {"success": False, "message": "Цель мертва"}
        if game.action_used.get(player_id):
            return {"success": False, "message": "Вы уже сделали выбор"}
        if action == Action.MAFIA_KILL.value:
            if game.phase != Phase.NIGHT:
                return {"success": False, "message": "Сейчас не ночь"}
            if game.players_roles.get(player_id) != Role.MAFIA:
                return {"success": False, "message": "Вы не мафия"}

            game.action_used[player_id] = True
            game.mafia_kill(target_id)
            return {"success": True, "message": "Голос принят"}

        elif action == Action.HEAL.value:
            if game.phase != Phase.NIGHT:
                return {"success": False, "message": "Сейчас не ночь"}
            if game.players_roles.get(player_id) != Role.DOCTOR:
                return {"success": False, "message": "Вы не доктор"}
            if target_id == player_id:
                if game.DOCTOR_self_heal_used:
                    return {"success": False, "message": "Вы не можете дважды себя вылечить"}
                game.DOCTOR_self_heal_used = True

            game.action_used[player_id] = True
            game.heal_player(target_id)
            return {"success": True, "message": "Выбор сделан"}

        elif action == Action.COMMISSIONER_KILL.value:
            if game.phase != Phase.NIGHT:
                return {"success": False, "message": "Сейчас не ночь"}
            if game.players_roles.get(player_id) != Role.COMMISSIONER:
                return {"success": False, "message": "Вы не комиссар"}
            if game.COMMISSIONER_kill_used:
                return {"success": False, "message": "Вы уже использовали убийство"}

            game.action_used[player_id] = True
            game.commissioner_kill(target_id)
            return {"success": True, "message": "Выбор сделан"}
        elif action == Action.COMMISSIONER_CHECK.value:
            if game.phase != Phase.NIGHT:
                return {"success": False, "message": "Сейчас не ночь"}
            if game.players_roles.get(player_id) != Role.COMMISSIONER:
                return {"success": False, "message": "Вы не комиссар"}

            game.action_used[player_id] = True
            result = game.commissioner_check(target_id)
            return {"success": True, "message": f"Выбранный игрок - {result}"}

        elif action == Action.VOTE.value:
            if game.phase != Phase.VOTING:
                return {"success": False, "message": "Сейчас не стадия голосования"}

            game.action_used[player_id] = True
            game.voting[player_id] = target_id
            return {"success": True, "message": "Голос принят"}

        return {"success": False, "message": "Неизвестное действие"}


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
        "has_acted": game.action_used.get(player_id, False),
        "mafia_team": game.get_mafia_team(player_id),
        "commissioner_kill_used": game.COMMISSIONER_kill_used
        if game.players_roles.get(player_id) == Role.COMMISSIONER else None,
        "commissioner_checks": game.COMMISSIONER_checks
        if game.players_roles.get(player_id) == Role.COMMISSIONER else {}
    }
