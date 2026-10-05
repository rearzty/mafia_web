import pytest

from app.game.core import Game
from app.game.config import Role, Phase
from app.game.websocket import handle_action, get_game_state


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


def make_started_game(n: int = 6) -> tuple[Game, list]:
    game = Game()
    players = make_players(n)
    for p in players:
        game.player_join(p)
    game.start_game()
    return game, players


def get_player_by_role(game: Game, role: Role) -> int:
    return next(pid for pid, r in game.players_roles.items() if r == role)


def test_start_game_fails_when_already_started():
    game, _ = make_started_game()
    roles = dict(game.players_roles)

    assert game.start_game() is False
    assert game.players_roles == roles
    assert len(game.mafias) == 1


@pytest.mark.asyncio
async def test_doctor_heal_saves_mafia_target():
    game, _ = make_started_game()
    game.phase = Phase.NIGHT
    mafia_id = get_player_by_role(game, Role.MAFIA)
    doctor_id = get_player_by_role(game, Role.DOCTOR)
    target_id = get_player_by_role(game, Role.CIVILIAN)

    await handle_action(game, mafia_id, "mafia_kill", target_id, "game", None)
    result = await handle_action(game, doctor_id, "heal", target_id, "game", None)
    game.end_night()
    revived = game.get_revived()

    assert result["success"] is True
    assert revived == game.players_usernames[target_id]
    assert game.get_killed() == []
    assert target_id not in game.dead


@pytest.mark.asyncio
async def test_failed_action_does_not_use_turn():
    game, _ = make_started_game()
    game.phase = Phase.DAY
    player_id = get_player_by_role(game, Role.CIVILIAN)
    target_id = get_player_by_role(game, Role.MAFIA)

    result = await handle_action(game, player_id, "vote", target_id, "game", None)
    assert result["success"] is False
    assert not game.action_used.get(player_id)

    game.phase = Phase.VOTING
    result = await handle_action(game, player_id, "vote", target_id, "game", None)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_invalid_target_and_message_types():
    game, _ = make_started_game()
    game.phase = Phase.VOTING
    player_id = game.players[0]

    result = await handle_action(game, player_id, "vote", "1", "game", None)
    assert result["success"] is False

    game.phase = Phase.DAY
    result = await handle_action(game, player_id, "chat", None, "game", 5)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_commissioner_can_only_check_or_kill_once_per_night():
    game, _ = make_started_game()
    game.phase = Phase.NIGHT
    commissioner_id = get_player_by_role(game, Role.COMMISSIONER)
    mafia_id = get_player_by_role(game, Role.MAFIA)

    result = await handle_action(game, commissioner_id, "commissioner_check", mafia_id, "game", None)
    assert result["message"] == f"Выбранный игрок - {Role.MAFIA.value}"

    result = await handle_action(game, commissioner_id, "commissioner_kill", mafia_id, "game", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_civilians_win_when_no_mafia_left():
    game, _ = make_started_game()
    game.dead.add(get_player_by_role(game, Role.MAFIA))

    game_over, winners = await game.check_winner()

    assert game_over is True
    assert len(winners) == 5


@pytest.mark.asyncio
async def test_mafia_wins_when_equal_to_civilians():
    game, _ = make_started_game()
    alive = [pid for pid in game.players if game.players_roles[pid] != Role.MAFIA]
    for pid in alive[:4]:
        game.dead.add(pid)

    game_over, winners = await game.check_winner()

    assert game_over is True
    assert winners == [game.players_usernames[get_player_by_role(game, Role.MAFIA)]]


@pytest.mark.asyncio
async def test_leave_during_game_marks_player_dead():
    game, players = make_started_game()
    game.phase = Phase.NIGHT
    leaver = players[0]

    game.player_leave(leaver)

    assert leaver.id in game.players
    assert leaver.id in game.dead
    assert not game.is_in_game(leaver.id)
    await game.check_winner()

    game.clean_game_on_end()
    assert leaver.id not in game.players
    assert leaver.id not in game.players_usernames


def test_mafia_team_visible_only_to_mafia():
    game, _ = make_started_game(10)
    mafia_id = game.mafias[0]
    civilian_id = get_player_by_role(game, Role.CIVILIAN)

    assert len(game.get_mafia_team(mafia_id)) == 2
    assert game.get_mafia_team(civilian_id) == []


@pytest.mark.asyncio
async def test_commissioner_checks_visible_only_to_commissioner():
    game, _ = make_started_game()
    game.phase = Phase.NIGHT
    commissioner_id = get_player_by_role(game, Role.COMMISSIONER)
    mafia_id = get_player_by_role(game, Role.MAFIA)

    await handle_action(game, commissioner_id, "commissioner_check", mafia_id, "game", None)

    mafia_name = game.players_usernames[mafia_id]
    assert get_game_state(game, commissioner_id)["commissioner_checks"] == {mafia_name: Role.MAFIA.value}
    assert get_game_state(game, mafia_id)["commissioner_checks"] == {}
