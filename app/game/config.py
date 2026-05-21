from enum import Enum


class GameConfig:
    MIN_PLAYERS: int = 6
    STARTING_TIME: int = 30
    WAIT_TIME: int = 10
    NIGHT_TIME: int = 30
    DAY_TIME: int = 30
    VOTING_TIME: int = 30


class Phase(Enum):
    WAITING = "waiting"
    STARTING = "starting"
    NIGHT = "night"
    DAY = "day"
    VOTING = "voting"


class Role(Enum):
    MAFIA = 'Мафия'
    DOCTOR = 'Доктор'
    CIVILIAN = 'Мирный'
    COMMISSIONER = 'Комиссар'


class Action(str, Enum):
    MAFIA_KILL = "mafia_kill"
    HEAL = "heal"
    COMMISSIONER_KILL = "commissioner_kill"
    VOTE = "vote"
