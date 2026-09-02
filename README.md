# Русь пролетарская

[![CI](https://github.com/plksnmm/rus-map/actions/workflows/ci.yml/badge.svg)](https://github.com/plksnmm/rus-map/actions/workflows/ci.yml)

«Русь пролетарская» — интерактивная карта мест промышленной и пролетарской
истории. Пользователи смогут находить и добавлять памятники, действующие и
утраченные заводы, фотографии, публикации и прогулочные маршруты.

Проект находится на ранней стадии разработки. Сейчас реализованы каркас
FastAPI-приложения, контракт списка мест, автоматические проверки и локальное
окружение PostgreSQL/PostGIS. Первая ORM-модель места хранит координаты как
PostGIS Point и управляется миграциями Alembic. Список мест читается из базы
через асинхронный repository, а новые места можно создавать через HTTP API.
Веб-клиент на React и TypeScript показывает адаптивный экран с интерактивной
картой MapLibre.

## Быстрый запуск

Требования: Git, [uv](https://docs.astral.sh/uv/), Docker и Node.js 24.

```powershell
uv sync
Copy-Item .env.example .env
docker compose up -d db
uv run uvicorn rus_map.main:app --reload
```

Во втором терминале запустить frontend:

```powershell
cd frontend
npm ci
npm run dev
```

После запуска доступны:

- проверка API: <http://127.0.0.1:8000/health>;
- Swagger UI: <http://127.0.0.1:8000/docs>;
- OpenAPI-схема: <http://127.0.0.1:8000/openapi.json>.
- интерактивная карта: <http://127.0.0.1:4173/>.

## Проверки качества

```powershell
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run alembic current
cd frontend
npm test
npm run lint
npm run build
```

## Документация

- [Установка и настройка](docs/SETUP.md)
- [Рабочий процесс разработчика](docs/DEVELOPMENT.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [HTTP API](docs/API.md)
- [База данных](docs/DATABASE.md)
- [Frontend](docs/FRONTEND.md)
- [Развёртывание staging](docs/DEPLOYMENT.md)
- [Тестирование](docs/TESTING.md)
- [Журнал проекта](docs/PROJECT_LOG.md)
- [Архитектурные решения](docs/decisions/)
