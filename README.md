# Русь пролетарская

[![CI](https://github.com/plksnmm/rus-map/actions/workflows/ci.yml/badge.svg)](https://github.com/plksnmm/rus-map/actions/workflows/ci.yml)

«Русь пролетарская» — интерактивная карта мест промышленной и пролетарской
истории. Пользователи смогут находить и добавлять памятники, действующие и
утраченные заводы, фотографии, публикации и прогулочные маршруты.

Проект находится на ранней стадии разработки. Сейчас реализованы каркас
FastAPI-приложения, контракт списка мест, автоматические проверки и локальное
окружение PostgreSQL/PostGIS. Первая ORM-модель места хранит координаты как
PostGIS Point и управляется миграциями Alembic. Список мест читается из базы
через асинхронный repository.

## Быстрый запуск

Требования: Git и [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
Copy-Item .env.example .env
docker compose up -d db
uv run uvicorn rus_map.main:app --reload
```

После запуска доступны:

- проверка API: <http://127.0.0.1:8000/health>;
- Swagger UI: <http://127.0.0.1:8000/docs>;
- OpenAPI-схема: <http://127.0.0.1:8000/openapi.json>.

## Проверки качества

```powershell
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run alembic current
```

## Документация

- [Установка и настройка](docs/SETUP.md)
- [Рабочий процесс разработчика](docs/DEVELOPMENT.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [HTTP API](docs/API.md)
- [База данных](docs/DATABASE.md)
- [Тестирование](docs/TESTING.md)
- [Журнал проекта](docs/PROJECT_LOG.md)
- [Архитектурные решения](docs/decisions/)
