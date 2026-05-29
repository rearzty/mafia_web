const gameId = window.GAME_ID;
let ws = null;
let currentPhase = window.PHASE || 'waiting';
let chatEnabled = true;


function connectWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/game/ws/${gameId}`);
    ws.onopen = () => console.log('WebSocket connected');
    ws.onmessage = (event) => handleWebSocketMessage(JSON.parse(event.data));
    ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };
    ws.onerror = (error) => console.error('WebSocket error:', error);
}

function handleWebSocketMessage(data) {
    console.log('WS:', data);

    switch (data.type) {
        case 'connected':
        case 'refresh':
        case 'phase_change':
        case 'player_joined':
        case 'player_left':
            void refreshUI();
            break;

        case 'night_results':
            showNightResults(data.killed, data.revived);
            void refreshUI();
            break;

        case 'voting_results':
            showVotingResults(data.voted_out, data.is_unique);
            void refreshUI();
            break;

        case 'game_started':
            void refreshUI();
            if (data.duration) startTimer(data.duration);
            break;

        case 'game_over':
            endGame(data.phase, data.duration, data.winners);
            break;

        case 'chat':
            addPlayerMessage(data.username, data.message);
            break;

        case 'action_result':
            showMessage(data.message, data.success ? 'success' : 'error');
            break;

        default:
            console.log('Unknown message type', data);
    }
}

async function refreshUI() {
    const res = await fetch(`/game/${gameId}/status`);
    if (res.ok) {
        const state = await res.json();
        createUI(state);
    }
}

function createUI(state) {
    updatePlayers(state.players);
    updatePhase(state.phase);
    if (state.my_role) {
        showRole(state.my_role);
    } else {
        document.getElementById('role-info').style.display = 'none';
        void updateActionButtons();
    }
}

function updatePlayers(players) {
    const container = document.getElementById('players-list');
    if (!container) return;

    container.innerHTML = players.map(p => `
        <div class="player-card" data-id="${p.id}">
            <span class="player-name">${escapeHtml(p.username)}</span>
            <span class="player-status">${p.is_dead ? '💀 Мёртв' : '❤️ Жив'}</span>
        </div>
    `).join('');
}

function updatePhase(phase) {
    currentPhase = phase;
    const phaseBadge = document.getElementById('phase-badge');
    if (phaseBadge) phaseBadge.textContent = phase;
    toggleChatByPhase(phase);
    void updateActionButtons();
}

function toggleChatByPhase(phase) {
    const chatInput = document.getElementById('chat-input');

    if (phase === 'night') {
        chatInput.disabled = true;
        chatInput.placeholder = 'Чат недоступен ночью...';
        addSystemMessage('🌙 Наступила ночь. Чат отключён');
    } else if (phase === 'voting') {
        chatInput.disabled = true;
        chatInput.placeholder = 'Идёт голосование, чат отключён...';
        addSystemMessage('🗳️ Голосование! Чат отключён');
    } else {
        chatInput.disabled = false;
        chatInput.placeholder = 'Введите сообщение...';
        if (phase === 'day') {
            addSystemMessage('☀️ Наступил день. Можно обсуждать!');
        } else if (phase === 'starting') {
            addSystemMessage('🎭 Ознакомьтесь с вашей ролью. Чат активен');
        }
    }
}


let timerInterval = null;

function startTimer(duration) {
    if (timerInterval) clearInterval(timerInterval);
    let remaining = duration;
    const timerEl = document.getElementById('timer');

    timerInterval = setInterval(() => {
        const mins = Math.floor(remaining / 60);
        const secs = remaining % 60;
        if (timerEl) timerEl.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
        remaining--;
        if (remaining < 0) clearInterval(timerInterval);
    }, 1000);
}

async function updateActionButtons() {
    const actionsDiv = document.getElementById('action-buttons');
    if (!actionsDiv) return;

    const res = await fetch(`/game/${gameId}/status`);
    if (!res.ok) return;
    const state = await res.json();
    const role = state.my_role;
    const hasActed = state.has_acted;
    const currentUserId = Number(window.USER_ID);

    if (currentPhase === 'waiting') {
        if (Number(state.players[0]?.id) === currentUserId) {
            actionsDiv.innerHTML = '<button onclick="startGame()" class="btn btn-success">Начать игру</button>';
        } else {
            actionsDiv.innerHTML = '<p>Ожидание начала игры...</p>';
        }
        return;
    }

    if (currentPhase === 'end') {
        actionsDiv.innerHTML = '<p>Игра завершена. Страница перезагрузится...</p>';
        return;
    }

    if (hasActed) {
        actionsDiv.innerHTML = '<p>Вы уже сделали ход в этой фазе. Ожидайте.</p>';
        return;
    }

    if (!role) {
        actionsDiv.innerHTML = '<p>Загрузка...</p>';
        return;
    }

    if (currentPhase === 'night') {
        if (role === 'Мафия') {
            renderTargetsList(state, 'mafia_kill', 'Выберите жертву');
        } else if (role === 'Доктор') {
            renderTargetsList(state, 'heal', 'Выберите игрока для лечения');
        } else if (role === 'Комиссар') {
            renderTargetsList(state, 'commissioner_kill', 'Выберите цель');
        } else {
            actionsDiv.innerHTML = '<p>Ожидание ночных действий...</p>';
        }
    } else if (currentPhase === 'voting') {
        renderTargetsList(state, 'vote', 'Голосование: выберите игрока');
    } else if (currentPhase === 'day') {
        actionsDiv.innerHTML = '<p>Обсуждение...</p>';
    } else if (currentPhase === 'starting') {
        actionsDiv.innerHTML = '<p>Ознакомьтесь с вашей ролью...</p>';
    }
}

function renderTargetsList(state, actionType, title) {
    const currentUserId = Number(window.USER_ID);
    const alive = state.players.filter(p => !p.is_dead && Number(p.id) !== currentUserId);
    const container = document.getElementById('action-buttons');
    if (!container) return;

    container.innerHTML = `
        <h4>${title}</h4>
        <div class="targets-list">
            ${alive.map(p => `<button class="target-btn" data-id="${p.id}">${escapeHtml(p.username)}</button>`).join('')}
        </div>
    `;

    document.querySelectorAll('.target-btn').forEach(btn => {
        btn.addEventListener('click', () => sendAction(actionType, parseInt(btn.dataset.id)));
    });
}

function sendAction(action, targetId) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({action, target_id: targetId}));
        const targetsContainer = document.querySelector('.targets-list');
        if (targetsContainer) {
            targetsContainer.innerHTML = '<p>✓ Выбор сделан</p>';
        }
    } else {
        showMessage('Нет соединения с сервером', 'error');
    }
}

async function startGame() {
    const res = await fetch(`/game/${gameId}/start`, {method: 'POST'});
    if (!res.ok) {
        const err = await res.json();
        showMessage(err.detail || 'Ошибка старта', 'error');
    }
}


function showNightResults(killed, revived) {
    let msg = '';
    if (killed.length) msg += `💀 Убит: ${killed.join(', ')}`;
    if (revived) msg += `\n❤️ Воскрешён: ${revived}`;
    addSystemMessage(msg || 'Ночь прошла без жертв');
}

function showVotingResults(votedOut, isUnique) {
    if (votedOut && isUnique) {
        addSystemMessage(`🗳️ Выгнан: ${votedOut}`);
    } else {
        addSystemMessage('🗳️ Никто не выгнан');
    }
}

function showGameOver(winners) {
    addSystemMessage(`🏆 Игра окончена! Победители: ${winners.join(', ')}`);
}

function endGame(currentPhase, duration, winners) {
    const phaseBadge = document.getElementById('phase-badge');
    if (phaseBadge) phaseBadge.textContent = currentPhase;
    showGameOver(winners);
    if (duration) startTimer(duration);
    setTimeout(() => {
        window.location.reload();
    }, duration * 1000);
}

function showMessage(msg, type) {
    const el = document.createElement('div');
    el.className = `message ${type}`;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

function escapeHtml(str) {
    return str.replace(/[&<>]/g, function (m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}


function toggleChat() {
    const messages = document.getElementById('chat-messages');
    const input = document.getElementById('chat-input-container');
    const toggle = document.querySelector('.chat-toggle');

    if (messages.style.display === 'none') {
        messages.style.display = 'flex';
        input.style.display = 'flex';
        toggle.textContent = '▲';
        chatEnabled = true;
    } else {
        messages.style.display = 'none';
        input.style.display = 'none';
        toggle.textContent = '▼';
        chatEnabled = false;
    }
}

function addSystemMessage(message) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message system';
    msgDiv.textContent = message;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

function addPlayerMessage(username, message) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message player';
    msgDiv.innerHTML = `<strong>${escapeHtml(username)}:</strong> ${escapeHtml(message)}`;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    if (input.disabled) {
        addSystemMessage('Чат сейчас недоступен');
        return;
    }

    const message = input.value.trim();
    if (!message) return;

    input.value = '';

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'chat',
            message: message
        }));
    }
}


function showRole(role) {
    const roleElement = document.getElementById('role-value');
    const roleContainer = document.getElementById('role-info');
    roleElement.textContent = role;
    updateRoleDescription(role);
    roleContainer.style.display = 'block';
    void updateActionButtons();
}

function toggleRole() {
    const desc = document.getElementById('role-description');
    const toggle = document.querySelector('.role-toggle');
    if (desc.style.display === 'none') {
        desc.style.display = 'block';
        toggle.textContent = '▼';
    } else {
        desc.style.display = 'none';
        toggle.textContent = '▲';
    }
}

function updateRoleDescription(role) {
    const abilities = {
        'Мафия': 'Ночью выбираете жертву',
        'Доктор': 'Ночью можете лечить одного игрока',
        'Комиссар': 'Ночью можете проверить или убить игрока',
        'Мирный': 'Голосуете днём, помогаете найти мафию'
    };
    document.getElementById('role-abilities').textContent = abilities[role] || 'Следуйте за ведущим';
}

connectWebSocket();
