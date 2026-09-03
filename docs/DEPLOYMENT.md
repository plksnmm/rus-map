# Развёртывание staging

Документ описывает staging-развёртывание «Руси пролетарской» на Ubuntu-сервере с уже работающими Caddy и
Vikunja. Публичный адрес карты — `https://vm-1703.lnvps.cloud/rus-map/`.

## Архитектура

| Компонент | Доступ | Назначение |
|---|---|---|
| host-Caddy | публичные порты 80 и 443 | TLS, маршрутизация Vikunja, карты и read-only API |
| `frontend` | `127.0.0.1:18080` | React-приложение с base path `/rus-map/` |
| `backend` | `127.0.0.1:18000` | FastAPI и полный API через SSH-туннель |
| `migrate` | только Docker-сеть | одноразовый запуск `alembic upgrade head` |
| `db` | только Docker-сеть | PostgreSQL/PostGIS и постоянный volume |
| Vikunja | `127.0.0.1:3456` | существующее приложение на корневом URL |

Caddy остаётся единственной публичной точкой входа и управляет HTTPS-сертификатом. Публичный маршрут карты
разрешает чтение API, но блокирует изменяющие запросы до реализации ключей участников. PostgreSQL не публикуется.

## Параметры сервера

- Ubuntu 24.04 LTS;
- 1 vCPU;
- 2 ГБ RAM;
- 2 ГБ постоянного swap;
- диск 100 ГБ;
- Docker Engine 29.7.2 и Compose 5.5.0;
- Caddy 2.11.4.

Текущее состояние ресурсов:

```bash
swapon --show
free -h
df -h /
```

## Подготовка каталога

Docker устанавливается из [официального APT-репозитория](https://docs.docker.com/engine/install/ubuntu/).
Репозиторий приложения размещается в `/opt/rus-map`:

```bash
sudo install -d -m 755 -o ubuntu -g ubuntu /opt/rus-map
git clone https://github.com/plksnmm/rus-map.git /opt/rus-map
cd /opt/rus-map
git status --short --branch
```

## Секреты

В Git хранится только `.env.production.example`. Рабочий `.env.production` содержит пароль PostgreSQL и
игнорируется Git.

```bash
cp .env.production.example .env.production
openssl rand -hex 32
nano .env.production
chmod 600 .env.production
```

Результат `openssl` нужно поместить в `POSTGRES_PASSWORD`. Шаблонный пароль на сервере использовать нельзя.

```bash
git check-ignore .env.production
git status --short
```

Первая команда должна вывести `.env.production`, а Git status должен остаться чистым.

## Первый запуск Docker-сервисов

До изменения Caddy приложение проверяется только через loopback:

```bash
docker compose --env-file .env.production -f compose.production.yml config --quiet
docker compose --env-file .env.production -f compose.production.yml up -d --build
docker compose --env-file .env.production -f compose.production.yml ps -a
```

Нормальное состояние:

- `db`, `backend` и `frontend` имеют статус `healthy`;
- `migrate` завершён с кодом `0`;
- backend и frontend опубликованы только на `127.0.0.1`;
- у `db` отсутствует host-привязка порта.

Проверка на сервере:

```bash
curl --fail http://127.0.0.1:18000/health
curl --fail http://127.0.0.1:18000/api/v1/places
curl --fail http://127.0.0.1:18080/
docker inspect --format '{{json .HostConfig.PortBindings}}' rus-map-production-db-1
```

У последней команды ожидается `{}`.

Production HTML должен содержать base path карты:

```bash
docker compose --env-file .env.production -f compose.production.yml exec -T frontend \
  grep -q '/rus-map/assets/' /usr/share/nginx/html/index.html
echo $?
```

Ожидаемый код — `0`.

## Подключение к существующему Caddy

В репозитории находятся:

- `deploy/caddy/rus-map.caddy` — маршруты карты и API;
- `deploy/caddy/Caddyfile.example` — полный ожидаемый Caddyfile с сохранённым fallback на Vikunja.

Сначала candidate проверяется без изменения работающего сервиса:

```bash
sudo cp deploy/caddy/Caddyfile.example /etc/caddy/Caddyfile.rus-map-candidate
sudo caddy fmt --overwrite /etc/caddy/Caddyfile.rus-map-candidate
sudo caddy validate --config /etc/caddy/Caddyfile.rus-map-candidate --adapter caddyfile
```

После успешной валидации создаётся резервная копия и применяется candidate:

```bash
sudo cp /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.backup-$(date +%F-%H%M%S)"
sudo cp /etc/caddy/Caddyfile.rus-map-candidate /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl is-active caddy
```

Если reload завершился ошибкой, работающий процесс Caddy продолжает использовать предыдущую конфигурацию. Нужно
вернуть последний backup-файл, повторить `caddy validate` и только затем reload.

## Публичная проверка

С рабочего компьютера или другого внешнего узла:

```bash
curl --fail https://vm-1703.lnvps.cloud/
curl --fail https://vm-1703.lnvps.cloud/rus-map/
curl --fail https://vm-1703.lnvps.cloud/rus-map/api/v1/places
curl --include --request POST https://vm-1703.lnvps.cloud/rus-map/api/v1/places
```

Ожидается:

- корневой URL продолжает возвращать Vikunja;
- `/rus-map/` возвращает React-приложение;
- публичный `GET` API успешен;
- публичный `POST` получает `403 Forbidden` от Caddy.

## Полный API через SSH-туннель

На рабочем компьютере:

```powershell
ssh -L 18000:127.0.0.1:18000 ubuntu@vm-1703.lnvps.cloud
```

Пока SSH-сессия открыта, Swagger доступен по адресу <http://127.0.0.1:18000/docs>. Backend не становится
публичным: соединение шифруется SSH и требует серверной аутентификации.

## Обновление

Перед обновлением CI ветки `main` должен быть зелёным:

```bash
cd /opt/rus-map
git pull --ff-only
docker compose --env-file .env.production -f compose.production.yml up -d --build
docker compose --env-file .env.production -f compose.production.yml ps -a
curl --fail https://vm-1703.lnvps.cloud/rus-map/
```

Compose дожидается здоровой базы, выполняет миграции, затем запускает backend. Миграции должны оставаться обратно
совместимыми с предыдущей версией приложения.

## Резервная копия PostgreSQL

Каталог для копий создаётся вне репозитория:

```bash
sudo install -d -m 700 -o "$USER" -g "$USER" /opt/rus-map-backups
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  pg_dump --format=custom --username=rus_map --dbname=rus_map \
  > /opt/rus-map-backups/rus-map-$(date +%F-%H%M%S).dump
ls -lh /opt/rus-map-backups
```

Восстановление изменяет данные и выполняется только после отдельной проверки выбранного dump-файла и остановки
записи в приложение.

## Откат приложения

Сначала фиксируется текущий commit и выбирается известный рабочий commit:

```bash
git rev-parse --short HEAD
git log --oneline -10
git switch --detach KNOWN_GOOD_COMMIT
docker compose --env-file .env.production -f compose.production.yml up -d --build
```

Возврат к актуальной ветке: `git switch main`. Alembic downgrade автоматически не выполняется, чтобы случайно не
потерять данные.

## Диагностика

```bash
docker compose --env-file .env.production -f compose.production.yml ps -a
docker compose --env-file .env.production -f compose.production.yml logs --tail=200 backend
docker compose --env-file .env.production -f compose.production.yml logs migrate
sudo systemctl status caddy --no-pager -l
sudo journalctl -u caddy --since '-30 minutes' --no-pager
docker stats --no-stream
free -h
df -h /
```

Остановка Docker-сервисов без удаления данных:

```bash
docker compose --env-file .env.production -f compose.production.yml down
```

Флаг `--volumes` намеренно не используется: он удалил бы базу.

## Справочные материалы

- [Caddy: `handle`](https://caddyserver.com/docs/caddyfile/directives/handle)
- [Caddy: `handle_path`](https://caddyserver.com/docs/caddyfile/directives/handle_path)
- [Docker Engine на Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
