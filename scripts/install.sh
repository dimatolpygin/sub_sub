#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Установщик Telegram-бота лид-магнита на Ubuntu (Docker).
# Postgres 16 и Redis предполагаются уже запущенными в Docker на этом сервере.
# Использование:  bash install.sh
# ─────────────────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
prompt()  { read -rp "$(echo -e "${YELLOW}>>> $1: ${NC}")" "$2"; }
promptp() { read -rsp "$(echo -e "${YELLOW}>>> $1: ${NC}")" "$2"; echo; }

echo ""
echo "=========================================================="
echo "   Sub Bot (лид-магнит) — установщик для Ubuntu"
echo "=========================================================="
echo ""

# ── Сбор переменных ──────────────────────────────────────────────────────────
prompt  "Git репозиторий (https://github.com/...)" GIT_REPO
GIT_REPO=${GIT_REPO:-https://github.com/dimatolpygin/sub_sub.git}

prompt  "Ветка для деплоя [master]" BRANCH
BRANCH=${BRANCH:-master}

prompt  "Каталог установки [/opt/sub_bot]" INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-/opt/sub_bot}

promptp "BOT_TOKEN (от @BotFather)" BOT_TOKEN
prompt  "CHANNEL_ID (@username или -100123456789)" CHANNEL_ID
prompt  "CHANNEL_URL (ссылка на канал; Enter — собрать из @username)" CHANNEL_URL
prompt  "ADMIN_IDS (id админов через запятую)" ADMIN_IDS

echo ""
warn "Подключение к УЖЕ работающим Postgres и Redis (в Docker)."
prompt  "DATABASE_URL [postgresql://postgres:postgres@localhost:5432/postgres]" DATABASE_URL
DATABASE_URL=${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/postgres}
prompt  "DB_SCHEMA [sub_bot]" DB_SCHEMA
DB_SCHEMA=${DB_SCHEMA:-sub_bot}
prompt  "REDIS_URL [redis://localhost:6379/0]" REDIS_URL
REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}

echo ""
prompt  "REMINDER_INTERVALS [1h,24h,72h]" REMINDER_INTERVALS
REMINDER_INTERVALS=${REMINDER_INTERVALS:-1h,24h,72h}

echo ""
info "Начинаю установку..."

# ── Docker ───────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  info "Устанавливаю Docker..."
  curl -fsSL https://get.docker.com | sh
fi
if ! docker compose version &>/dev/null; then
  error "Не найден плагин 'docker compose'. Установите docker-compose-plugin и повторите."
fi
info "Docker: $(docker --version)"

# ── git ──────────────────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
  info "Устанавливаю git..."
  apt-get update -qq && apt-get install -y -qq git
fi

# ── Клонирование / обновление ────────────────────────────────────────────────
if [[ -d "$INSTALL_DIR/.git" ]]; then
  warn "Каталог уже существует — обновляю..."
  cd "$INSTALL_DIR"
  git fetch --all
  git checkout "$BRANCH"
  git reset --hard "origin/$BRANCH"
else
  info "Клонирую репозиторий ($BRANCH)..."
  git clone --branch "$BRANCH" "$GIT_REPO" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# ── .env ─────────────────────────────────────────────────────────────────────
info "Создаю .env..."
cat > .env <<ENVEOF
BOT_TOKEN=${BOT_TOKEN}
CHANNEL_ID=${CHANNEL_ID}
CHANNEL_URL=${CHANNEL_URL}
ADMIN_IDS=${ADMIN_IDS}
DATABASE_URL=${DATABASE_URL}
DB_SCHEMA=${DB_SCHEMA}
REDIS_URL=${REDIS_URL}
REMINDER_INTERVALS=${REMINDER_INTERVALS}
REMINDER_CHECK_INTERVAL_MIN=5
SUB_CACHE_TTL=60
LOG_LEVEL=INFO
ENVEOF
chmod 600 .env

# ── Запуск ───────────────────────────────────────────────────────────────────
info "Собираю и запускаю контейнер..."
docker compose up -d --build

echo ""
echo "=========================================================="
info "Установка завершена!"
echo ""
echo "  Каталог:   ${INSTALL_DIR}"
echo "  Логи:      docker compose -f ${INSTALL_DIR}/docker-compose.yml logs -f"
echo "  Рестарт:   docker compose -f ${INSTALL_DIR}/docker-compose.yml restart"
echo "  Стоп:      docker compose -f ${INSTALL_DIR}/docker-compose.yml down"
echo ""
warn "Не забудьте сделать бота администратором канала ${CHANNEL_ID}!"
echo "=========================================================="
