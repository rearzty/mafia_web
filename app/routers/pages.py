from datetime import timedelta

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.core.dependencies import get_current_user, get_current_user_optional, get_token
from app.core.security import create_access_token
from app.db.models import User
from app.game.dependencies import get_player_in_game
from app.game.storage import mafia_games, mafia_players
from app.game.core import Phase

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(get_current_user_optional)):
    return templates.TemplateResponse(request, "index.html", {"user": user})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: User = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request, "login.html")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: User = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request, "register.html")


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "profile.html", {"user": user})


@router.get("/lobby", response_class=HTMLResponse)
async def lobby_page(request: Request, user: User = Depends(get_current_user)):
    available_games = []
    for gid, game in mafia_games.items():
        if game.phase == Phase.WAITING:
            available_games.append({
                "id": gid,
                "players_count": len(game.players),
                "status": game.phase.value
            })

    current_game_id = mafia_players.get(user.id)
    current_game_data = None
    if current_game_id and current_game_id in mafia_games:
        game = mafia_games[current_game_id]
        current_game_data = {
            "id": current_game_id,
            "players_count": len(game.players)
        }

    return templates.TemplateResponse(request, "lobby.html", {
        "user": user,
        "available_games": available_games,
        "current_game": current_game_data
    })


@router.get("/game/{game_id}", response_class=HTMLResponse)
async def game_page(request: Request, game_id: str, user: User = Depends(get_player_in_game)):
    game = mafia_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if user.id not in game.players:
        raise HTTPException(status_code=403, detail="You are not in this game")

    return templates.TemplateResponse(request, "game.html", {
        "user": user,
        "ws_token": create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=5)),
        "game_id": game_id,
        "game": game,
        "phase": game.phase.value
    })
