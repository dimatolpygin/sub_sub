#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Установщик Telegram-бота лид-магнита на Ubuntu (Docker, самодостаточный стек).
# Поднимает бот + свои Postgres и Redis в одном docker-compose.
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
prompt  "CHANNEL_URL (ссылка на канал; Enter — определит сам)" CHANNEL_URL
prompt  "ADMIN_IDS (id админов через запятую)" ADMIN_IDS

echo ""
prompt  "REMINDER_INTERVALS [1h,24h,72h]" REMINDER_INTERVALS
REMINDER_INTERVALS=${REMINDER_INTERVALS:-1h,24h,72h}

# Пароль для встроенного Postgres генерируется автоматически.
POSTGRES_PASSWORD=$(openssl rand -hex 24)

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
# Если .env уже есть — сохраняем прежний пароль БД, чтобы не потерять доступ к данным.
if [[ -f .env ]] && grep -q '^POSTGRES_PASSWORD=' .env; then
  POSTGRES_PASSWORD=$(grep '^POSTGRES_PASSWORD=' .env | head -1 | cut -d= -f2-)
  warn "Использую существующий POSTGRES_PASSWORD из .env"
fi

info "Создаю .env..."
cat > .env <<ENVEOF
BOT_TOKEN=${BOT_TOKEN}
CHANNEL_ID=${CHANNEL_ID}
CHANNEL_URL=${CHANNEL_URL}
ADMIN_IDS=${ADMIN_IDS}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DB_SCHEMA=sub_bot
REMINDER_INTERVALS=${REMINDER_INTERVALS}
REMINDER_CHECK_INTERVAL_MIN=1
SUB_CACHE_TTL=60
LOG_LEVEL=INFO
ENVEOF
chmod 600 .env

# ── Запуск ───────────────────────────────────────────────────────────────────
info "Собираю и запускаю стек (бот + Postgres + Redis)..."
docker compose up -d --build

echo ""
echo "=========================================================="
info "Установка завершена!"
echo ""
echo "  Каталог:   ${INSTALL_DIR}"
echo "  Логи:      docker compose -f ${INSTALL_DIR}/docker-compose.yml logs -f bot"
echo "  Рестарт:   docker compose -f ${INSTALL_DIR}/docker-compose.yml restart"
echo "  Стоп:      docker compose -f ${INSTALL_DIR}/docker-compose.yml down"
echo ""
warn "Не забудьте сделать бота администратором канала ${CHANNEL_ID}!"
echo "=========================================================="
