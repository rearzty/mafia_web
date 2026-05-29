import asyncio
from app.game.core import Game, Phase
from app.game.config import GameConfig
from app.game.storage import mafia_games
from app.game.websocket import manager, get_game_state


async def end_game(game_id, winners):
    game = mafia_games[game_id]
    game.phase = Phase.END
    await manager.broadcast(game_id, {
        "type": "game_over",
        "winners": [w for w in winners] if winners else [],
        "message": "Game Over",
        "duration": GameConfig.RESTARTING_TIME,
        'phase': Phase.END.value
    })
    await asyncio.sleep(GameConfig.RESTARTING_TIME)
    mafia_games[game_id].clean_game_on_end()
    for user_id in game.players:
        await manager.send_to_player(game_id, user_id, {
            "type": "refresh",
            **get_game_state(game, user_id)
        })


async def starting_phase(game_id: str, game: Game):
    await asyncio.sleep(GameConfig.STARTING_TIME)

    async with game.lock:
        if game.phase != Phase.STARTING:
            return

        game.phase = Phase.NIGHT
        game.clean_actions()

        await manager.broadcast(game_id, {
            "type": "phase_change",
            "phase": game.phase.value,
            "duration": GameConfig.NIGHT_TIME
        })

        asyncio.create_task(night_phase(game_id, game))


async def night_phase(game_id: str, game: Game):
    await asyncio.sleep(GameConfig.NIGHT_TIME)

    async with game.lock:
        if game.phase != Phase.NIGHT:
            return

        game.end_night()

        killed_usernames = game.get_killed()
        revived_username = game.get_revived()
        game.clean_actions()

        await manager.broadcast(game_id, {
            "type": "night_results",
            "killed": killed_usernames,
            "revived": revived_username
        })

        game_over, winners = await game.check_winner()
        if game_over:
            asyncio.create_task(end_game(game_id, winners))
            return

        game.phase = Phase.DAY
        await manager.broadcast(game_id, {
            "type": "phase_change",
            "phase": Phase.DAY.value,
            "duration": GameConfig.DAY_TIME
        })

        asyncio.create_task(day_phase(game_id, game))


async def day_phase(game_id: str, game: Game):
    await asyncio.sleep(GameConfig.DAY_TIME)

    async with game.lock:
        if game.phase != Phase.DAY:
            return

        game.phase = Phase.VOTING
        await manager.broadcast(game_id, {
            "type": "phase_change",
            "phase": Phase.VOTING.value,
            "duration": GameConfig.VOTING_TIME
        })

        asyncio.create_task(voting_phase(game_id, game))


async def voting_phase(game_id: str, game: Game):
    await asyncio.sleep(GameConfig.VOTING_TIME)

    async with game.lock:
        if game.phase != Phase.VOTING:
            return

        voted_out_username, is_unique = game.get_voting_results()

        await manager.broadcast(game_id, {
            "type": "voting_results",
            "voted_out": voted_out_username,
            "is_unique": is_unique
        })

        game_over, winners = await game.check_winner()
        if game_over:
            asyncio.create_task(end_game(game_id, winners))
            return

        game.clean_actions()
        game.phase = Phase.NIGHT
        await manager.broadcast(game_id, {
            "type": "phase_change",
            "phase": Phase.NIGHT.value,
            "duration": GameConfig.NIGHT_TIME
        })

        asyncio.create_task(night_phase(game_id, game))
