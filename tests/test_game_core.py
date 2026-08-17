from app.game.core import Game
from app.game.config import Role, Phase


def make_players(n: int):
    from app.schemas.user import UserResponse
    return [UserResponse(id=i, email=f"u{i}@test.com", username=f"user{i}") for i in range(n)]


def test_player_join_adds_to_players_list():
    game = Game()
    players = make_players(1)
    game.player_join(players[0])

    assert game.players == [0]
    assert game.players_usernames[0] == "user0"


def test_start_game_fails_with_too_few_players():
    game = Game()
    for p in make_players(3):
        game.player_join(p)

    result = game.start_game()

    assert result is False
    assert game.phase == Phase.WAITING


def test_start_game_assigns_all_roles():
    game = Game()
    for p in make_players(10):
        game.player_join(p)

    result = game.start_game()

    assert result is True
    assert game.phase == Phase.STARTING
    assert len(game.players_roles) == 10
    assert len(game.mafias) == 3
