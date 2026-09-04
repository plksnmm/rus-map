# Развёртывание staging

Документ описывает staging-развёртывание «Руси пролетарской» на Ubuntu-сервере с уже работающими Caddy и
Vikunja. Публичный адрес карты — `https://vm-1703.lnvps.cloud/rus-map/`.

Если явно не указано иное, блоки `bash` выполняются на Ubuntu-сервере, а блоки `powershell` — на локальном
Windows-компьютере. Серверные и локальные команды нельзя объединять в одном терминале.

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

## Защита существующей Vikunja

Vikunja должна принимать соединения только через Caddy. Перед изменением systemd создаётся встроенный dump Vikunja:

```bash
sudo install -d -m 700 /var/backups/vikunja
sudo sh -c 'cd /opt/vikunja && /usr/local/bin/vikunja dump \
  --path /var/backups/vikunja --filename before-loopback-bind-$(date +%F-%H%M%S)'
sudo ls -lh /var/backups/vikunja
```

Loopback-привязка задаётся отдельным systemd drop-in, поэтому пакетный unit-файл не редактируется:

```bash
sudo install -d -m 755 /etc/systemd/system/vikunja.service.d
printf '[Service]\nEnvironment=VIKUNJA_SERVICE_INTERFACE=127.0.0.1:3456\n' | \
  sudo tee /etc/systemd/system/vikunja.service.d/10-loopback.conf > /dev/null
sudo systemctl daemon-reload
sudo systemctl restart vikunja
sudo systemctl is-active vikunja
sudo ss -lntp | grep ':3456'
```

Ожидается `active` и listener `127.0.0.1:3456`, а не `0.0.0.0:3456` или `*:3456`. После перезапуска Caddy-маршрут
Vikunja должен вернуть HTTP 200.

## Публичная проверка

С локального Windows-компьютера:

```powershell
$base = "https://vm-1703.lnvps.cloud"
curl.exe -sS -o NUL -w "vikunja=%{http_code}`n" "$base/"
curl.exe -sS -o NUL -w "map=%{http_code}`n" "$base/rus-map/"
curl.exe -sS -o NUL -w "api-get=%{http_code}`n" "$base/rus-map/api/v1/places"
curl.exe -sS -o NUL -w "post=%{http_code}`n" -X POST "$base/rus-map/api/v1/places"
curl.exe -sS -o NUL -w "put=%{http_code}`n" -X PUT "$base/rus-map/api/v1/places"
curl.exe -sS -o NUL -w "patch=%{http_code}`n" -X PATCH "$base/rus-map/api/v1/places"
curl.exe -sS -o NUL -w "delete=%{http_code}`n" -X DELETE "$base/rus-map/api/v1/places"
```

Ожидается:

- корневой URL продолжает возвращать Vikunja;
- `/rus-map/` возвращает React-приложение;
- публичный `GET` API успешен;
- публичные `POST`, `PUT`, `PATCH` и `DELETE` получают `403 Forbidden` от Caddy.

Прямой порт Vikunja проверяется с локального Windows-компьютера, а не с сервера:

```powershell
curl.exe -I --connect-timeout 3 --max-time 5 http://vm-1703.lnvps.cloud:3456
$LASTEXITCODE
```

Ожидается тайм-аут и код curl `28`. Ответ HTTP 200 означал бы, что plaintext-порт снова опубликован в интернете.

## Полный API через SSH-туннель

На рабочем компьютере:

```powershell
ssh -L 18000:127.0.0.1:18000 ubuntu@vm-1703.lnvps.cloud
```

Пока SSH-сессия открыта, Swagger доступен по адресу <http://127.0.0.1:18000/docs>. Backend не становится
публичным: соединение шифруется SSH и требует серверной аутентификации.

## Обновление

Перед обновлением CI ветки `main` должен быть зелёным. На сервере сначала проверяются рабочая ветка и отсутствие
неучтённых изменений, фиксируется текущий commit и создаётся бэкап по инструкции из `docs/BACKUPS.md`:

```bash
cd /opt/rus-map
git status --short --branch
git rev-parse --short HEAD
```

Если status содержит локальные изменения, обновление останавливается до их разбора. После создания и проверки
бэкапа:

```bash
git pull --ff-only
docker compose --env-file .env.production -f compose.production.yml config --quiet
docker compose --env-file .env.production -f compose.production.yml up -d --build
docker compose --env-file .env.production -f compose.production.yml ps -a
curl --fail http://127.0.0.1:18000/health
curl --fail https://vm-1703.lnvps.cloud/rus-map/
curl --fail https://vm-1703.lnvps.cloud/rus-map/api/v1/places
```

Compose дожидается здоровой базы, выполняет миграции, затем запускает backend. Миграции должны оставаться обратно
совместимыми с предыдущей версией приложения.

## Резервная копия PostgreSQL

Полная процедура создания, проверки, тестовой репетиции и аварийного восстановления описана в
[`docs/BACKUPS.md`](BACKUPS.md). Dump создаётся перед каждым обновлением с миграциями и перед любым восстановлением.
Dump-файлы хранятся вне Git с правами `600`.

Проверенное добавление текстов и ссылок выполняется отдельной закрытой
CLI-командой внутри backend-контейнера. Перед фактическим импортом обязателен
свежий backup и успешный `--dry-run`. Полный порядок приведён в
[`docs/MATERIAL_IMPORT.md`](MATERIAL_IMPORT.md).

Новые проверенные точки импортируются похожей закрытой командой. Порядок
проверки координат, backup, dry-run и production-запуска описан в
[`docs/PLACE_IMPORT.md`](PLACE_IMPORT.md).

## Контрольный чек-лист staging

- `https://vm-1703.lnvps.cloud/` возвращает Vikunja с HTTP 200;
- `https://vm-1703.lnvps.cloud/rus-map/` возвращает карту с HTTP 200;
- `https://vm-1703.lnvps.cloud/rus-map/favicon.png` возвращает HTTP 200;
- публичный `GET /rus-map/api/v1/places` возвращает HTTP 200;
- публичные изменяющие методы API возвращают HTTP 403;
- `db`, `backend` и `frontend` работают, `migrate` завершён с кодом 0;
- backend и frontend слушают только loopback-порты;
- PostgreSQL не имеет host port binding;
- Vikunja слушает только `127.0.0.1:3456`;
- последний dump PostgreSQL имеет права `600` и читается через `pg_restore --list`;
- `.env.production` имеет права `600`, игнорируется Git и не выводится в журналы.

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

Если Nginx возвращает `403` для существующего статического файла, нужно
проверить права внутри frontend-контейнера. Production-сборка выполняет
нормализацию прав: каталоги получают `755`, а обычные файлы — `644`. Поэтому
непривилегированный worker-процесс Nginx может читать файлы и обходить каталоги,
но статические ресурсы не получают лишний признак исполняемого файла.

Остановка Docker-сервисов без удаления данных:

```bash
docker compose --env-file .env.production -f compose.production.yml down
```

Флаг `--volumes` намеренно не используется: он удалил бы базу.

## Справочные материалы

- [Caddy: `handle`](https://caddyserver.com/docs/caddyfile/directives/handle)
- [Caddy: `handle_path`](https://caddyserver.com/docs/caddyfile/directives/handle_path)
- [Docker Engine на Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
