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
    const response = await fetch(`/game/${gameId}/leave`, {method: 'POST'});
    if (response.ok) {
        window.location.href = '/lobby';
    }
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

            if (!password) {
                errorDiv.textContent = 'Введите пароль';
                return;
            }
            if (password.length < 6) {
                errorDiv.textContent = 'Пароль должен быть не менее 6 символов';
                return;
            }
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
            } else if (response.status === 422) {
                errorDiv.textContent = 'Проверьте данные: email должен быть корректным, username 3-50 символов (латиница, цифры, _), пароль 6-50 символов';
            } else {
                const error = await response.json();
                errorDiv.textContent = error.detail || 'Ошибка регистрации';
            }
        };
    }
});

function initLoginForm() {
    const form = document.getElementById('loginForm');
    if (!form) return;

    form.onsubmit = async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const errorDiv = document.getElementById('error');

        try {
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
        } catch (err) {
            errorDiv.textContent = 'Ошибка соединения';
        }
    };
}

function sendResetLink() {
    const email = document.getElementById('email').value;
    const messageDiv = document.getElementById('message');
    if (!email) {
        const messageDiv = document.getElementById('message');
        messageDiv.textContent = 'Введите email';
        messageDiv.style.color = '#e74c3c';
        return;
    }

    fetch('/auth/forgot-password', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email: email})
    })
        .then(response => {
            if (response.status === 429) {
                return response.json().then(data => {
                    throw {type: 'rate_limit', message: data.detail || 'Слишком много попыток. Подождите минуту.'};
                });
            }
            if (!response.ok) {
                return response.json().then(data => {
                    throw {type: 'error', message: data.detail || 'Ошибка запроса'};
                });
            }
            return response.json();
        })
        .then(data => {
            messageDiv.textContent = data.message;
            messageDiv.style.color = '#2ecc71';
            messageDiv.style.display = 'block';
            document.getElementById('forgotPasswordForm').reset();
        })
        .catch(error => {
            messageDiv.textContent = error.message || 'Ошибка соединения с сервером';
            messageDiv.style.color = '#e74c3c';
            messageDiv.style.display = 'block';
        });
}

async function setNewPassword() {
    const token = document.getElementById('token').value;
    const newPassword = document.getElementById('new_password').value;
    const messageDiv = document.getElementById('message');

    if (!newPassword) {
        messageDiv.className = 'message-error';
        messageDiv.textContent = 'Введите новый пароль';
        messageDiv.style.display = 'block';
        return;
    }

    if (newPassword.length < 6) {
        messageDiv.className = 'message-error';
        messageDiv.textContent = 'Пароль должен содержать минимум 6 символов';
        messageDiv.style.display = 'block';
        return;
    }

    try {
        const response = await fetch('/auth/reset-password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({reset_token: token, new_password: newPassword})
        });

        const data = await response.json();

        if (response.ok) {
            messageDiv.className = 'message-success';
            messageDiv.textContent = 'Пароль успешно изменён!';
            messageDiv.style.display = 'block';
            setTimeout(() => window.location.href = '/login', 2000);
        } else if (response.status === 429) {
            messageDiv.className = 'message-error';
            messageDiv.textContent = data.detail || 'Слишком много попыток. Подождите минуту.';
            messageDiv.style.display = 'block';
        } else {
            messageDiv.className = 'message-error';
            messageDiv.textContent = data.detail || 'Ошибка при сбросе пароля';
            messageDiv.style.display = 'block';
        }
    } catch (error) {
        messageDiv.className = 'message-error';
        messageDiv.textContent = 'Ошибка соединения с сервером';
        messageDiv.style.display = 'block';
    }
}