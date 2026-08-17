# 🎭 Mafia Game

Браузерная многопользовательская игра в мафию с real-time коммуникацией через WebSocket.

## Стек

- **FastAPI** — веб-фреймворк
- **SQLAlchemy (async) + asyncpg** — ORM и драйвер PostgreSQL
- **PostgreSQL** — основная база данных (пользователи)
- **Redis** — кэширование текущего пользователя, rate limiting
- **Celery + RabbitMQ** — асинхронная отправка email (сброс пароля)
- **WebSocket** — real-time игровой процесс
- **Alembic** — миграции БД
- **Jinja2** — серверные шаблоны
- **JWT (httponly cookie)** — аутентификация
- **Docker / docker-compose** — локальный запуск всей системы
- **pytest** — тесты игровой логики

## Возможности

- Регистрация и авторизация пользователей
- Создание и подключение к игровым комнатам
- Real-time игровой процесс через WebSocket
- Роли: Мафия, Доктор, Комиссар, Мирный житель
- Фазы: Ночь → День → Голосование
- Сброс пароля по email (письмо отправляется асинхронно через Celery)
- Rate limiting на чувствительных эндпоинтах

## Структура проекта

```
app/
├── main.py              # Точка входа
├── core/                 # Инфраструктура
│   ├── config.py          # Настройки (pydantic-settings, .env)
│   ├── security.py        # Хэширование паролей/токенов, JWT
│   ├── cache.py            # Redis-кэш текущего пользователя
│   ├── redis_client.py     # Подключение к Redis
│   ├── email.py             # Отправка писем (SMTP)
│   └── celery/               # Celery-приложение и задачи (отправка email)
├── db/                    # Слой данных (модели, CRUD, подключение)
├── game/                  # Игровая логика
│   ├── core.py              # Класс Game — состояние игры
│   ├── phase.py              # Управление фазами (таймеры)
│   ├── websocket.py           # ConnectionManager + обработка действий
│   ├── storage.py              # Хранилище активных игр (in-memory)
│   └── config.py                # Роли, фазы, константы
├── routers/               # HTTP и WebSocket роуты
├── schemas/                # Pydantic-схемы
├── middleware/              # Rate limiting
├── templates/                # HTML-шаблоны
└── static/                    # CSS, JS

tests/                    # pytest — тесты игровой логики
alembic/                   # Миграции БД
docker-compose.yaml        # postgres, redis, rabbitmq, migrate, api, celery
Dockerfile
```

## Запуск через Docker (рекомендуется)

Поднимает всё сразу: PostgreSQL, Redis, RabbitMQ, применяет миграции, стартует API и Celery-воркер.

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd mafia_web
```

### 2. Настроить переменные окружения

Создать `.env` в корне проекта:

```env
POSTGRES_DB=mafia_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_PORT=5432

SECRET_KEY=your-secret-key

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your@email.com

APP_URL=http://localhost:8000

RABBITMQ_USER=mafia
RABBITMQ_PASSWORD=your-password

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

### 3. Собрать и запустить

```bash
docker-compose up --build
```

Сервис `migrate` применит Alembic-миграции перед стартом `api` (ждёт готовности PostgreSQL через healthcheck). `api` и `celery` стартуют только после того, как PostgreSQL, Redis и RabbitMQ станут healthy.

Приложение доступно по адресу: `http://localhost:8000`
Панель RabbitMQ: `http://localhost:15672`

## Запуск без Docker (локальная разработка)

Требуются локально установленные и запущенные PostgreSQL, Redis и RabbitMQ.

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

pip install -r requirements.txt

alembic upgrade head

# Терминал 1 — API
uvicorn app.main:app --reload

# Терминал 2 — Celery-воркер (для отправки email)
celery -A app.core.celery.app:celery_app worker --loglevel=INFO
```

Значения `.env` — как в примере выше, только `POSTGRES_HOST=localhost`, `REDIS_HOST=localhost`, `RABBITMQ_HOST=localhost`.

## Тесты

```bash
pytest tests/ -v
```

Пока покрыта только базовая игровая логика (`app/game/core.py`) — присоединение игроков, старт игры, распределение ролей. HTTP/WebSocket-эндпоинты и работа с БД тестами пока не покрыты.

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
5. Мафия побеждает, когда их количество ≥ количества живых мирных
6. Мирные побеждают, когда вся мафия устранена