function logout() {
    fetch('/auth/logout', {method: 'POST'})
        .then(() => window.location.href = '/');
}

async function createGame() {
    const res = await fetch('/game/create', {method: 'POST'});
    if (res.ok) {
        const data = await res.json();
        await joinGame(data.game_id);
    }
}

async function joinGame(gameId) {
    const res = await fetch(`/game/${gameId}/join`, {method: 'POST'});
    if (res.ok) {
        window.location.href = `/game/${gameId}`;
    }
}

async function leaveGame(gameId) {
    await fetch(`/game/${gameId}/leave`, {method: 'POST'});
    location.reload();
}

document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.onsubmit = async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('error');

            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: new URLSearchParams({username: email, password: password})
            });

            if (response.ok) {
                window.location.href = '/';
            } else {
                const error = await response.json();
                errorDiv.textContent = error.detail || 'Ошибка входа';
            }
        };
    }

    const regForm = document.getElementById('registerForm');
    if (regForm) {
        regForm.onsubmit = async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('error');

            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, username, password})
            });

            if (response.ok) {
                const loginRes = await fetch('/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: new URLSearchParams({username: email, password: password})
                });
                if (loginRes.ok) window.location.href = '/';
                else window.location.href = '/login';
            } else {
                const error = await response.json();
                errorDiv.textContent = error.detail || 'Ошибка регистрации';
            }
        };
    }
});