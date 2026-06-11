-- Хранилище настроек бота, изменяемых на лету (например, расписание напоминаний).
CREATE TABLE IF NOT EXISTS bot_settings (
    key        TEXT        PRIMARY KEY,
    value      TEXT        NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
