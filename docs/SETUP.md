# Установка и настройка

## Необходимые инструменты

- Git;
- uv;
- Docker Desktop с Linux containers;
- Node.js 24 и npm;
- PyCharm или другой редактор с поддержкой Python.

Python отдельно устанавливать не обязательно: `uv` установит версию из файла
`.python-version` и создаст изолированное окружение `.venv`.

На Windows Node.js можно установить через NVM for Windows. В текущем локальном
окружении NVM, Node.js и npm cache находятся на диске `D:`. Проверка:

```powershell
nvm current
node --version
npm --version
npm config get cache
```

## Подготовка проекта

Из корневой папки репозитория выполнить:

```powershell
uv sync
```

Команда устанавливает обычные и dev-зависимости в `.venv` в соответствии с
`pyproject.toml` и `uv.lock`.

Создать локальные переменные окружения и запустить базу данных:

```powershell
Copy-Item .env.example .env
docker compose up -d db
docker compose ps
```

В Git хранится только безопасный шаблон `.env.example`. Локальный `.env` не
отслеживается. Подробные команды приведены в `docs/DATABASE.md`.

Установить frontend-зависимости строго из lock-файла:

```powershell
cd frontend
npm ci
cd ..
```

Подробный запуск и устранение проблем описаны в `docs/FRONTEND.md`.

## Настройка PyCharm

Открыть корневую папку проекта и выбрать существующий интерпретатор:

```text
D:\rus_map\.venv\Scripts\python.exe
```

Локальная папка `.idea` не входит в Git: настройки IDE могут отличаться у
разных разработчиков.

## Проверка установки

```powershell
uv run python --version
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy src
cd frontend
npm test
npm run lint
npm run build
```

Все команды должны завершаться без ошибок и предупреждений.
