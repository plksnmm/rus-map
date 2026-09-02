# Развёртывание staging

Документ описывает staging-развёртывание «Руси пролетарской» на одном Ubuntu-сервере без доменного имени.
Пользователь открывает приложение по публичному IPv4-адресу через HTTPS. PostgreSQL не публикуется наружу.

## Архитектура

| Компонент | Доступ | Назначение |
|---|---|---|
| `gateway` | публичные порты 80 и 443 | TLS, frontend и read-only API |
| `frontend` | `127.0.0.1:18080` | собранное React-приложение |
| `backend` | `127.0.0.1:18000` | FastAPI и полный API через SSH-туннель |
| `migrate` | только Docker-сеть | одноразовый запуск `alembic upgrade head` |
| `db` | только Docker-сеть | PostgreSQL/PostGIS и постоянный volume |

Публичный gateway разрешает `GET` к `/api/`, но блокирует изменяющие запросы. Это временная граница безопасности
до реализации ключей участников. Swagger и полный API доступны владельцу через SSH-туннель.

## Требования

- Ubuntu 24.04 LTS;
- 1 vCPU, 2 ГБ RAM и 2 ГБ swap достаточно для текущего staging;
- не менее 10 ГБ свободного места;
- Docker Engine с Compose plugin;
- публичный IPv4-адрес;
- входящие TCP-порты 22, 80 и 443 в firewall провайдера и Ubuntu.

На сервере проекта используется 100 ГБ диска. Перед первым развёртыванием swap проверяется командой
`swapon --show`.

## Файлы и секреты

В Git хранится только `.env.production.example`. Рабочий `.env.production` содержит пароль PostgreSQL и
игнорируется Git.

```bash
cp .env.production.example .env.production
openssl rand -hex 32
nano .env.production
chmod 600 .env.production
```

Результат `openssl` нужно поместить в `POSTGRES_PASSWORD`. Шаблонное значение нельзя использовать на сервере.
Проверка, что секрет не отслеживается:

```bash
git status --short
git check-ignore .env.production
```

## Первый запуск приложения

Команды выполняются из каталога репозитория:

```bash
docker compose --env-file .env.production -f compose.production.yml config --quiet
docker compose --env-file .env.production -f compose.production.yml up -d --build
docker compose --env-file .env.production -f compose.production.yml ps -a
```

Нормальное состояние:

- `db`, `backend` и `frontend` имеют статус `healthy`;
- `migrate` завершён с кодом `0`;
- у `db` нет host-привязки порта;
- backend и frontend опубликованы только на `127.0.0.1`.

Локальная проверка на сервере:

```bash
curl --fail http://127.0.0.1:18000/health
curl --fail http://127.0.0.1:18000/api/v1/places
curl --fail http://127.0.0.1:18080/
docker inspect --format '{{json .HostConfig.PortBindings}}' rus-map-production-db-1
```

У последней команды ожидается `{}`.

## HTTPS по IP-адресу

Let’s Encrypt выдаёт сертификаты для IP только с профилем `shortlived`. Они действуют 160 часов, поэтому
автоматическое продление обязательно. Нужен Certbot 5.4 или новее; Compose использует закреплённый образ 5.8.0.

Сначала запускается временный HTTP-сервер для ACME challenge:

```bash
docker compose --env-file .env.production -f compose.production.yml \
  --profile tls-bootstrap up -d gateway-bootstrap
curl --fail http://PUBLIC_IP/healthz
```

`PUBLIC_IP` в командах ниже нужно заменить настоящим адресом, а `EMAIL` — почтой администратора. Сначала
проверяется тестовый центр сертификации, который не создаёт доверенный браузером сертификат:

```bash
docker compose --env-file .env.production -f compose.production.yml run --rm certbot \
  certonly --staging --preferred-profile shortlived --webroot \
  --webroot-path /var/www/certbot --ip-address PUBLIC_IP \
  --cert-name rus-map-ip-test --email EMAIL --agree-tos --no-eff-email --non-interactive
```

После успешной проверки тестовую lineage можно удалить и запросить рабочий сертификат:

```bash
docker compose --env-file .env.production -f compose.production.yml run --rm certbot \
  delete --cert-name rus-map-ip-test --non-interactive

docker compose --env-file .env.production -f compose.production.yml run --rm certbot \
  certonly --preferred-profile shortlived --webroot \
  --webroot-path /var/www/certbot --ip-address PUBLIC_IP \
  --cert-name rus-map-staging --email EMAIL --agree-tos --no-eff-email --non-interactive
```

Переключение с bootstrap на постоянный gateway:

```bash
docker compose --env-file .env.production -f compose.production.yml \
  --profile tls-bootstrap stop gateway-bootstrap
docker compose --env-file .env.production -f compose.production.yml \
  --profile public up -d gateway
```

Проверки выполняются с другого компьютера:

```bash
curl --fail https://PUBLIC_IP/healthz
curl --fail https://PUBLIC_IP/api/v1/places
curl --include --request POST https://PUBLIC_IP/api/v1/places
```

Первые две команды должны завершиться успешно, публичный `POST` — вернуть `403 Forbidden`.

## Автоматическое продление сертификата

Файл `/etc/systemd/system/rus-map-renew.service`:

```ini
[Unit]
Description=Renew Rus Map IP certificate
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/rus-map
ExecStart=/usr/bin/docker compose --env-file .env.production -f compose.production.yml run --rm certbot renew --quiet
ExecStartPost=/usr/bin/docker compose --env-file .env.production -f compose.production.yml exec -T gateway nginx -s reload
```

Файл `/etc/systemd/system/rus-map-renew.timer`:

```ini
[Unit]
Description=Check Rus Map IP certificate twice daily

[Timer]
OnCalendar=*-*-* 03,15:00:00
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

Активация и проверка:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rus-map-renew.timer
systemctl list-timers rus-map-renew.timer
docker compose --env-file .env.production -f compose.production.yml run --rm certbot renew --dry-run
```

## Полный API через SSH-туннель

На рабочем компьютере:

```powershell
ssh -L 18000:127.0.0.1:18000 ubuntu@PUBLIC_IP
```

Пока SSH-сессия открыта, Swagger доступен локально по адресу <http://127.0.0.1:18000/docs>. Порт backend не
становится публичным: SSH шифрует соединение и требует серверную аутентификацию.

## Обновление

Перед обновлением нужно убедиться, что CI в `main` зелёный:

```bash
git pull --ff-only
docker compose --env-file .env.production -f compose.production.yml \
  --profile public up -d --build
docker compose --env-file .env.production -f compose.production.yml ps -a
curl --fail https://PUBLIC_IP/healthz
```

Compose сначала дожидается здоровой базы, выполняет миграции, затем запускает backend. Миграции должны оставаться
обратно совместимыми с предыдущей версией приложения.

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

Сначала фиксируется текущий commit и выбирается известный рабочий commit из истории:

```bash
git rev-parse --short HEAD
git log --oneline -10
git switch --detach KNOWN_GOOD_COMMIT
docker compose --env-file .env.production -f compose.production.yml \
  --profile public up -d --build
```

Возврат к актуальной ветке: `git switch main`. Alembic downgrade автоматически не выполняется, чтобы случайно не
потерять данные.

## Диагностика

```bash
docker compose --env-file .env.production -f compose.production.yml ps -a
docker compose --env-file .env.production -f compose.production.yml logs --tail=200 backend
docker compose --env-file .env.production -f compose.production.yml logs --tail=200 gateway
docker compose --env-file .env.production -f compose.production.yml logs migrate
docker stats --no-stream
free -h
df -h /
```

Остановка контейнеров без удаления данных:

```bash
docker compose --env-file .env.production -f compose.production.yml \
  --profile public down
```

Флаг `--volumes` здесь намеренно не используется: он удалил бы базу и сертификаты.

## Справочные материалы

- [Let’s Encrypt: IP-сертификаты и Certbot](https://letsencrypt.org/2026/03/11/shorter-certs-certbot)
- [Certbot: webroot и автоматическое продление](https://eff-certbot.readthedocs.io/en/stable/using.html)
- [Docker Engine на Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
