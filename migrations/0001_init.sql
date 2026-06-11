-- Начальная схема бота лид-магнита.
-- Таблицы создаются без указания схемы — они попадают в нашу схему благодаря search_path,
-- настроенному в пуле соединений (см. src/db.py). Существующие схемы не затрагиваются.

-- Пользователи бота и их прогресс по воронке «подписка → подарок».
CREATE TABLE IF NOT EXISTS users (
    tg_id            BIGINT      PRIMARY KEY,
    username         TEXT,
    first_name       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    subscribed       BOOLEAN     NOT NULL DEFAULT FALSE,
    subscribed_at    TIMESTAMPTZ,
    gift_sent        BOOLEAN     NOT NULL DEFAULT FALSE,
    gift_sent_at     TIMESTAMPTZ,
    reminders_sent   INTEGER     NOT NULL DEFAULT 0,   -- сколько напоминаний уже отправлено
    last_reminder_at TIMESTAMPTZ,
    reminders_done   BOOLEAN     NOT NULL DEFAULT FALSE -- TRUE = лимит напоминаний исчерпан
);

-- Индекс для планировщика: быстро находить, кому ещё актуально слать напоминания.
CREATE INDEX IF NOT EXISTS idx_users_pending
    ON users (created_at)
    WHERE gift_sent = FALSE AND reminders_done = FALSE;

-- Текущий лид-магнит (один файл). Храним как singleton: всегда строка с id = 1.
CREATE TABLE IF NOT EXISTS lead_magnet (
    id          SMALLINT    PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    file_id     TEXT        NOT NULL,   -- Telegram file_id документа
    file_name   TEXT,
    caption     TEXT,                   -- подпись, отправляемая вместе с файлом
    mime_type   TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  BIGINT                  -- tg_id админа, заменившего файл
);
