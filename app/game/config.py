from enum import Enum


class Phase(Enum):
    RESTARTING = "restarting"
    WAITING = "waiting"
    STARTING = "starting"
    NIGHT = "night"
    DAY = "day"
    VOTING = "voting"
    END = "end"


class Role(Enum):
    MAFIA = 'Мафия'
    DOCTOR = 'Доктор'
    CIVILIAN = 'Мирный'
    COMMISSIONER = 'Комиссар'


class Action(str, Enum):
    MAFIA_KILL = "mafia_kill"
    HEAL = "heal"
    COMMISSIONER_KILL = "commissioner_kill"
    COMMISSIONER_CHECK = "commissioner_check"
    VOTE = "vote"


class GameConfig:
    MIN_PLAYERS: int = 6
    STARTING_TIME: int = 15
    WAIT_TIME: int = 10
    NIGHT_TIME: int = 30
    DAY_TIME: int = 30
    VOTING_TIME: int = 30
    RESTARTING_TIME: int = 10
    ROLES = [Role.MAFIA, Role.DOCTOR, Role.COMMISSIONER,
             Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN,
             Role.MAFIA, Role.CIVILIAN, Role.MAFIA, Role.CIVILIAN]
