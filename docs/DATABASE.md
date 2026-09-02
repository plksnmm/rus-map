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
