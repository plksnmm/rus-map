# Импорт фотографий мест

Фотографии хранятся не по временным URL Telegram, а в собственном постоянном
Docker-томе приложения. В базе находятся метаданные и связь файла с версией
материала. Публично выдаются только изображения опубликованных материалов.

## Что делает импортёр

Команда `rus-map-import-images`:

- принимает только JPEG, PNG и WebP размером до 25 MiB;
- сверяет обязательный SHA-256 исходного файла;
- блокирует абсолютные пути и `..`;
- учитывает ориентацию EXIF;
- уменьшает изображение до 1920 px по большей стороне;
- создаёт WebP для сайта, сохраняя исходник отдельно;
- создаёт `MediaAsset`, материал типа `image` и неизменяемую ревизию;
- повторно проверяет уже импортированные UUID и не создаёт дубли;
- в режиме `--dry-run` не пишет ни БД, ни файлы.

Название материала используется как доступный `alt`-текст фотографии. Поле
`source_url` хранит постоянную ссылку на публикацию или каталог, а не временный
адрес CDN.

## Формат манифеста

```json
{
  "schema_version": 1,
  "place_id": "bbe880f1-4bf5-4b49-889a-7ccab143a6dd",
  "images": [
    {
      "media_id": "NEW-STABLE-UUID",
      "material_id": "NEW-STABLE-UUID",
      "revision_id": "NEW-STABLE-UUID",
      "revision_number": 1,
      "status": "published",
      "title": "Кусковский химический завод, 1964 год",
      "source": "Государственный каталог Музейного фонда РФ",
      "source_url": "https://t.me/rus_proletarskaya/266",
      "file": "kuskovo/factory-1964.jpg",
      "sha256": "64 lowercase hexadecimal characters"
    }
  ]
}
```

UUID генерируются один раз командой `uv run python -c "import uuid; print(uuid.uuid4())"`
и после публикации не меняются.

## Подготовка файлов в Windows

Исходники складываются, например, в `content/media/kuskovo/`. Хэш вычисляется
без изменения файла:

```powershell
Get-FileHash content\media\kuskovo\factory-1964.jpg -Algorithm SHA256
```

PowerShell выводит хэш заглавными буквами; в JSON его нужно записать строчными.
Перед коммитом обязательно проверить право на публикацию, подпись, источник и
соответствие фотографии выбранному месту.

Локальная проверка с работающей PostgreSQL:

```powershell
uv run python -m rus_map.admin.image_import `
  --file content\places\PLACE-images.json `
  --assets-dir content\media `
  --dry-run
```

## Импорт на сервере

Сначала создаётся резервная копия БД и медиа по `docs/BACKUPS.md`. Затем из
`/opt/rus-map` выполняется dry-run. Каталог с проверенными исходниками
подключается только для чтения:

```bash
docker compose --env-file .env.production -f compose.production.yml run --rm -T \
  --volume "$PWD/content/media:/imports:ro" \
  backend python -m rus_map.admin.image_import \
  --file - --assets-dir /imports --dry-run \
  < content/places/PLACE-images.json
```

После успешной проверки запускается та же команда без `--dry-run`:

```bash
docker compose --env-file .env.production -f compose.production.yml run --rm -T \
  --volume "$PWD/content/media:/imports:ro" \
  backend python -m rus_map.admin.image_import \
  --file - --assets-dir /imports \
  < content/places/PLACE-images.json
```

Повторный запуск должен завершиться успешно и показать нули в `created`.

## Telegram

Автоматический Telegram-приём будет отдельным адаптером над тем же манифестом.
Бот получает новые `channel_post`, если добавлен в канал, но обновления Bot API
хранятся не дольше 24 часов. Поэтому старые публикации безопаснее пересылать
боту вручную, а новые принимать автоматически. Каждый результат сначала имеет
статус `pending_review`; автоматическая публикация запрещена.

Полная история канала потребовала бы TDLib и пользовательской авторизации с
`api_id`/`api_hash`, поэтому этот более чувствительный вариант не входит в
текущую задачу.

Официальная документация: [Bot API](https://core.telegram.org/bots/api),
[TDLib](https://core.telegram.org/tdlib/getting-started).
