import asyncio
import random
from asyncio import Lock

from app.db.models import User
from app.game.config import Phase, Role, GameConfig


class Game:
    roles = [Role.MAFIA, Role.DOCTOR, Role.COMMISSIONER,
             Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN,
             Role.MAFIA, Role.CIVILIAN, Role.MAFIA, Role.CIVILIAN]

    def __init__(self):
        self.phase = Phase.WAITING
        self.players: list[int] = []
        self.dead: list[int] = []
        self.killed_this_night: list[int] = []
        self.players_roles: dict[int, Role] = {}
        self.players_usernames: dict[int, str] = {}
        self.mafias: list[int] = []
        self.mafia_votes: dict[int, int] = {}
        self.voting: dict[int, int] = {}
        self.revived: int | None = None
        self.COMMISSIONER_kill_used: bool = False
        self.DOCTOR_self_heal_used: bool = False
        self.messages_to_be_removed: list[dict] = []
        self.action_used: dict[int, bool] = {}
        self.lock: Lock = asyncio.Lock()

    def start_game(self) -> bool:
        players = self.players
        playing = len(players)
        if playing < GameConfig.MIN_PLAYERS:
            return False
        current_roles = self.roles[:playing:]
        random.shuffle(current_roles)
        players_roles = self.players_roles
        for i in range(playing):
            players_roles[players[i]] = current_roles[i]
            if current_roles[i] == Role.MAFIA:
                self.mafias.append(players[i])
        self.phase = Phase.STARTING
        return True

    def player_join(self, player: User):
        self.players.append(player.id)
        self.players_usernames[player.id] = player.username

    def player_leave(self, player: User):
        if player.id not in self.players:
            return
        self.players.remove(player.id)
        self.players_usernames.pop(player.id, None)

    def heal_player(self, player_id: int, doctor_id: int):
        if player_id == doctor_id:
            self.DOCTOR_self_heal_used = True
        self.revived = player_id

    def commissioner_kill(self, player_id: int):
        if player_id not in self.killed_this_night:
            self.killed_this_night.append(player_id)
        self.COMMISSIONER_kill_used = True

    def mafia_kill(self, player_id: int):
        if player_id not in self.mafia_votes:
            self.mafia_votes[player_id] = 0
        self.mafia_votes[player_id] += 1

    def end_night(self):
        if self.mafia_votes:
            mafia_results = {}
            for choice in self.mafia_votes:
                if self.mafia_votes[choice] not in mafia_results:
                    mafia_results[self.mafia_votes[choice]] = []
                mafia_results[self.mafia_votes[choice]].append(choice)
            if len(mafia_results[max(mafia_results.keys())]) > 1:
                target = random.choice(mafia_results[max(mafia_results.keys())])
            else:
                target = mafia_results[max(mafia_results.keys())][0]
            if target not in self.killed_this_night:
                self.killed_this_night.append(target)

    def get_revived(self) -> str | None:
        if self.revived and self.revived in self.killed_this_night:
            revived: str | None = self.players_usernames[self.revived]
            self.killed_this_night.remove(self.revived)
            return revived
        return None

    def get_killed(self) -> list[str]:
        killed: list[str] = []
        for killed_id in self.killed_this_night:
            killed_username = self.players_usernames[killed_id]
            killed.append(killed_username)
            self.dead.append(killed_id)
        return killed

    def clean_actions(self):
        self.messages_to_be_removed = []
        self.revived = None
        self.killed_this_night = []
        self.mafia_votes = {}
        self.action_used = {}
        self.voting = {}

    def get_voting_results(self) -> tuple[str, bool]:
        results = {}
        max_votes = 0
        max_votes_user_id: int = 0
        for vote in self.voting:
            if not results.get(self.voting[vote]):
                results[self.voting[vote]] = 0
            results[self.voting[vote]] += 1
            if results[self.voting[vote]] > max_votes:
                max_votes = results[self.voting[vote]]
                max_votes_user_id = self.voting[vote]
        is_unique_winner = list(results.values()).count(max_votes) == 1
        max_votes_username = self.players_usernames.get(max_votes_user_id, '')
        if is_unique_winner and max_votes_username:
            self.dead.append(max_votes_user_id)
        return max_votes_username, is_unique_winner

    async def check_winner(self) -> tuple[bool, list[str]]:
        mafias_alive = []
        alive = []
        for player_id in self.players:
            player_username = self.players_usernames[player_id]
            if player_id not in self.dead:
                alive.append(player_id)
                if self.players_roles[player_id] == Role.MAFIA:
                    mafias_alive.append(player_id)
        if len(mafias_alive) * 2 >= len(alive):
            mafias_players: list[str] = [self.players_usernames[player_id] for player_id in mafias_alive]
            return True, mafias_players
        elif len(mafias_alive) == 0:
            alive_players: list[str] = [self.players_usernames[player_id] for player_id in alive]
            return False, alive_players
        return False, []
