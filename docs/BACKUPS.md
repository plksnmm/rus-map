# Резервное копирование и восстановление

Документ описывает ручное резервное копирование PostgreSQL/PostGIS на staging-сервере и аварийное восстановление.
Команды выполняются в терминале Ubuntu на сервере из каталога `/opt/rus-map`. Dump-файлы содержат пользовательские
данные и не должны попадать в Git.

## Где хранятся копии

Локальные копии хранятся вне репозитория в закрытом каталоге `/opt/rus-map-backups`:

```bash
sudo install -d -m 700 -o "$USER" -g "$USER" /opt/rus-map-backups
ls -ld /opt/rus-map-backups
```

Ожидаемые права каталога — `drwx------`. Наличие копии на том же сервере защищает от ошибки при обновлении, но не от
поломки или потери самого сервера. До появления автоматизации важные dump-файлы нужно дополнительно переносить в
зашифрованное внешнее хранилище.

## Создание копии PostgreSQL

Сначала задаётся уникальное имя файла и включается закрытая маска прав:

```bash
cd /opt/rus-map
umask 077
backup_file="/opt/rus-map-backups/rus-map-$(date +%F-%H%M%S).dump"
```

Затем `pg_dump` запускается внутри контейнера базы. Формат `custom` позволяет проверять архив через `pg_restore` и
выбирать отдельные объекты при восстановлении:

```bash
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  pg_dump --format=custom --username=rus_map --dbname=rus_map > "$backup_file"
echo $?
chmod 600 "$backup_file"
ls -lh "$backup_file"
```

Код `0` и ненулевой размер файла обязательны. Пароль в команду и имя файла не добавляется.

## Проверка архива

## Копия изображений

PostgreSQL dump не содержит фотографии. После появления `media_data` вместе с
каждым важным dump создаётся отдельный архив тома:

```bash
media_backup="/opt/rus-map-backups/rus-map-media-$(date +%F-%H%M%S).tar.gz"
docker run --rm \
  --volume rus-map-production_media_data:/media:ro \
  --volume /opt/rus-map-backups:/backup \
  alpine:3.22 tar -czf "/backup/$(basename "$media_backup")" -C /media .
chmod 600 "$media_backup"
tar -tzf "$media_backup" | head
ls -lh "$media_backup"
```

Код завершения должен быть `0`, архив — ненулевого размера, а список должен
содержать каталоги `original/` и `display/` после первого импорта. Dump базы и
архив медиа образуют одну логическую резервную копию и переносятся во внешнее
зашифрованное хранилище вместе.

Проверка списка объектов не изменяет базу:

```bash
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  pg_restore --list < "$backup_file" | head -n 15
```

Ожидается заголовок `PostgreSQL database dump`, формат `CUSTOM` и список объектов без ошибок. Такая проверка
подтверждает, что архив читается, но полноценную возможность восстановления гарантирует только периодическая
тестовая репетиция в отдельной базе.

## Поиск и выбор копии

Нельзя восстанавливать «последний попавшийся» файл. Сначала нужно явно посмотреть доступные копии и назначить
конкретный путь:

```bash
ls -lht /opt/rus-map-backups
restore_file="/opt/rus-map-backups/EXACT_BACKUP_NAME.dump"
test -s "$restore_file"
echo $?
```

Перед дальнейшими действиями `echo $?` должен вернуть `0`. Имя выбранного файла нужно сохранить в журнале
инцидента или заметках обслуживания.

## Безопасная репетиция восстановления

Репетиция создаёт отдельную базу и не затрагивает рабочую `rus_map`. Её следует выполнять при отдельной задаче на
обслуживание, когда на диске достаточно места:

```bash
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  createdb --username=rus_map rus_map_restore_test
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  pg_restore --exit-on-error --no-owner --no-privileges \
  --username=rus_map --dbname=rus_map_restore_test < "$restore_file"
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  psql --username=rus_map --dbname=rus_map_restore_test \
  --command="SELECT count(*) FROM app.places;"
```

Тестовую базу удаляют только после успешной проверки и только явно указанным именем:

```bash
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  dropdb --username=rus_map rus_map_restore_test
```

## Аварийное восстановление рабочей базы

> Эта процедура уничтожает текущее содержимое рабочей базы. Её нельзя выполнять как обычную проверку.

Перед восстановлением должны быть выбраны и проверены `restore_file`, причина восстановления и известный рабочий
commit приложения. Запись останавливается вместе с backend, а текущее состояние сохраняется отдельным аварийным
dump-файлом.

```bash
cd /opt/rus-map
docker compose --env-file .env.production -f compose.production.yml stop backend
emergency_file="/opt/rus-map-backups/before-restore-$(date +%F-%H%M%S).dump"
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  pg_dump --format=custom --username=rus_map --dbname=rus_map > "$emergency_file"
chmod 600 "$emergency_file"
```

Только после проверки аварийного файла рабочая база пересоздаётся и наполняется выбранным архивом:

```bash
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  psql --username=rus_map --dbname=postgres --set=ON_ERROR_STOP=1 \
  --command="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'rus_map' AND pid <> pg_backend_pid();"
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  dropdb --username=rus_map rus_map
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  createdb --username=rus_map rus_map
docker compose --env-file .env.production -f compose.production.yml exec -T db \
  pg_restore --exit-on-error --no-owner --no-privileges \
  --username=rus_map --dbname=rus_map < "$restore_file"
```

Если `pg_restore` завершился ошибкой, backend не запускается до выяснения причины. После успешного восстановления:

```bash
docker compose --env-file .env.production -f compose.production.yml up -d backend
docker compose --env-file .env.production -f compose.production.yml ps -a
curl --fail http://127.0.0.1:18000/health
curl --fail https://vm-1703.lnvps.cloud/rus-map/api/v1/places
```

## Удаление старых копий

Автоматическая политика хранения пока не настроена. Перед удалением сначала выводится полный список:

```bash
ls -lht /opt/rus-map-backups
```

Удалять можно только явно выбранный файл после подтверждения наличия более новой проверенной копии. Нельзя применять
маски, рекурсивное удаление или удалять весь каталог `/opt/rus-map-backups`.

## Проверенный первый бэкап

3 сентября 2026 года создан первый staging-dump:

- формат: PostgreSQL custom dump;
- версия PostgreSQL и `pg_dump`: 18.6;
- архив содержит 32 TOC-записи;
- список объектов успешно прочитан через `pg_restore --list`;
- файл имеет права `600`;
- восстановление на рабочей базе не выполнялось.
