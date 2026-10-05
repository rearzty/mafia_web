from pydantic import BaseModel


class GameResponse(BaseModel):
    game_id: str


class PlayerInfo(BaseModel):
    id: int
    username: str
    is_dead: bool


class GameStatusResponse(BaseModel):
    phase: str
    players: list[PlayerInfo]
    my_role: str | None
    has_acted: bool
    mafia_team: list[str]
    commissioner_kill_used: bool | None
    commissioner_checks: dict[str, str]
