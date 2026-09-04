# База данных

## Состав локального окружения

Docker Compose запускает PostgreSQL 18 с расширением PostGIS 3.6 из образа
`postgis/postgis:18-3.6`.

| Параметр | Значение |
| --- | --- |
| Compose service | `db` |
| Host | `127.0.0.1` |
| Host port | `15432` |
| Container port | `5432` |
| Database | `rus_map` |
| User | `rus_map` |
| Named volume | `rus-map_postgres_data` |

Host-порт отличается от стандартного, потому что на рабочей Windows-системе
порт `5432` входит в зарезервированный диапазон. Привязка к `127.0.0.1` не
публикует базу в локальную сеть.

## Первый запуск

```powershell
Copy-Item .env.example .env
docker compose up -d db
docker compose ps
```

Готовая база имеет состояние `healthy`.

## Проверка PostgreSQL и PostGIS

```powershell
docker compose exec db psql -U rus_map -d rus_map -c "SELECT current_database(), current_user, PostGIS_Version();"
```

Запрос должен вернуть базу и пользователя `rus_map`, а также версию PostGIS.

Та же проверка через асинхронный Python-слой:

```powershell
uv run python -m rus_map.db.check
```

## SQLAlchemy

`src/rus_map/db/session.py` предоставляет:

- `get_engine()` — общий асинхронный engine с проверкой соединений;
- `get_session_factory()` — фабрику SQLAlchemy sessions;
- `get_session()` — одну session для будущей FastAPI dependency.

Используется драйвер `asyncpg`. Изначально рассматривался Psycopg 3, но его
асинхронный режим несовместим со стандартным `ProactorEventLoop` Windows.

## Миграции Alembic

```powershell
# Показать текущую ревизию базы
uv run alembic current

# Применить все миграции
uv run alembic upgrade head

# Проверить, есть ли изменения ORM без миграции
uv run alembic check
```

Alembic читает подключение из `.env` через общий класс `Settings`. Фиктивный или
настоящий URL с паролем не хранится в `alembic.ini`.

Таблицы приложения размещаются в отдельной схеме PostgreSQL `app`. Alembic
проверяет только эту схему и не управляет служебными объектами расширений PostGIS
в схемах `public`, `tiger` и `topology`. Поэтому вывод команды `alembic check` не
должен предлагать удаление `spatial_ref_sys` или таблиц геокодера PostGIS.

Первая ревизия `e14eff9a3f10` создаёт схему `app`, таблицу `app.places` и
пространственный GiST-индекс. Координаты хранятся как `geometry(Point,4326)`, где
SRID 4326 соответствует широте и долготе WGS 84.

Ревизия `28388488c1fd` добавляет:

- `app.materials` — материалы, связанные внешним ключом с местом;
- `app.material_revisions` — пронумерованные неизменяемые редакции материала;
- статусы `pending_review`, `published`, `rejected`, `archived` отдельно для
  материала и редакции;
- типы `text`, `external_link`, `image`, `video`, `audio`;
- уникальность пары `material_id + revision_number`;
- CHECK-ограничение: редакция содержит либо текст, либо URL, но не оба значения;
- CHECK-ограничение для непустого текста и URL, начинающегося с `http://` или
  `https://`;
- индексы для выборки материалов места и последней опубликованной редакции.

Раздельные статусы нужны для безопасного редактирования. Материал может оставаться
`published`, пока его новая редакция находится в `pending_review`; публичное
чтение в это время продолжает использовать предыдущую опубликованную редакцию.
Физическое удаление не является обычным способом модерации: записи переводятся
в `rejected` или `archived`, сохраняя историю.

Откат `uv run alembic downgrade base` удаляет всю схему `app`. Его можно
выполнять только на пустой локальной или специально выделенной тестовой базе.
Для обычной проверки миграций без удаления данных используются `alembic current`,
`alembic check` и integration-тест структуры базы.

## Диагностика

```powershell
docker compose ps
docker compose logs db --tail 50
docker compose config --quiet
```

## Остановка

```powershell
docker compose down
```

Команда удаляет контейнер и сеть, но сохраняет данные в named volume. При
следующем `docker compose up -d db` база будет восстановлена из этого volume.

Команда `docker compose down --volumes` удаляет и volume с данными. Её можно
использовать только для осознанного полного сброса локальной базы.

## Переменные окружения

`.env.example` содержит безопасный локальный пример. Настоящие пароли и
production-конфигурация никогда не должны попадать в Git. Изменения переменных
инициализации PostgreSQL применяются только при создании пустого volume.
# Медиафайлы

`app.media_assets` хранит SHA-256 исходника и WebP, безопасные относительные
ключи, MIME-типы, размеры файлов и ширину/высоту. Двоичные данные находятся в
постоянном томе `media_data`, а не в PostgreSQL. Колонка
`app.material_revisions.media_asset_id` связывает изображение с конкретной
неизменяемой ревизией материала.
