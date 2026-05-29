# 🎭 Mafia Game

Браузерная многопользовательская игра в мафию с real-time коммуникацией через WebSocket.

## Стек

- **FastAPI** — веб-фреймворк
- **SQLAlchemy** — ORM
- **PostgreSQL** — база данных
- **Redis** — кэширование
- **WebSocket** — real-time коммуникация
- **Jinja2** — шаблоны
- **JWT** — аутентификация через cookie

## Возможности

- Регистрация и авторизация пользователей
- Создание и подключение к игровым комнатам
- Real-time игровой процесс через WebSocket
- Роли: Мафия, Доктор, Комиссар, Мирный житель
- Фазы: Ночь → День → Голосование
- Сброс пароля по email
- Rate limiting на чувствительных эндпоинтах

## Структура проекта

```
app/
├── main.py              # Точка входа
├── core/                # Инфраструктура (конфиг, безопасность, кэш, email, redis)
├── db/                  # Слой данных (модели, CRUD, подключение)
├── game/                # Игровая логика
│   ├── core.py          # Класс Game — состояние игры
│   ├── phase.py         # Управление фазами (таймеры)
│   ├── websocket.py     # ConnectionManager + обработка действий
│   ├── storage.py       # Хранилище активных игр
│   └── config.py        # Роли, фазы, константы
├── routers/             # HTTP и WebSocket роуты
├── schemas/             # Pydantic-схемы
├── middleware/          # Rate limiting
├── templates/           # HTML-шаблоны
└── static/              # CSS, JS
```

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd <repo-name>
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить переменные окружения

Скопировать `.env.example` в `.env` и заполнить:

```bash
cp .env.example .env
```

```env
DATABASE_URL=postgresql://user:password@localhost:5432/mafia
SECRET_KEY=your-secret-key
REDIS_URL=redis://localhost:6379

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-password
FROM_EMAIL=your@email.com
```

### 5. Применить миграции

```bash
alembic upgrade head
```

### 6. Запустить

```bash
uvicorn app.main:app --reload
```

Приложение доступно по адресу: `http://localhost:8000`

## API

Документация доступна по адресу `http://localhost:8000/docs` после запуска.

### Аутентификация

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Вход |
| POST | `/auth/logout` | Выход |
| POST | `/auth/forgot-password` | Запрос сброса пароля |
| POST | `/auth/reset-password` | Сброс пароля по токену |

### Игра

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/game/create` | Создать игру |
| POST | `/game/{game_id}/join` | Войти в игру |
| POST | `/game/{game_id}/leave` | Выйти из игры |
| POST | `/game/{game_id}/start` | Запустить игру (только создатель) |
| GET | `/game/{game_id}/status` | Статус игры |
| WS | `/game/ws/{game_id}` | WebSocket соединение |

### WebSocket — формат сообщений

Отправка действия:
```json
{
  "action": "mafia_kill",
  "target_id": 42
}
```

Доступные действия: `mafia_kill`, `heal`, `commissioner_kill`, `commissioner_check`, `vote`, `chat`.

## Игровой процесс

1. Игрок создаёт комнату → получает `game_id`
2. Остальные игроки подключаются по `game_id`
3. Создатель запускает игру
4. Игра проходит по фазам: **Старт → Ночь → День → Голосование → Ночь → ...**
5. Мафия побеждает когда их количество ≥ количества живых мирных
6. Мирные побеждают когда вся мафия устранена
