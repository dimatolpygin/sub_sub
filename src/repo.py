"""Доступ к данным (repository). Тонкая обёртка над SQL-запросами."""
from __future__ import annotations

import asyncpg


# ─────────────────────────── Пользователи ───────────────────────────

async def upsert_user(
    pool: asyncpg.Pool, tg_id: int, username: str | None, first_name: str | None
) -> None:
    """Создаёт пользователя при первом /start или обновляет его username/имя."""
    await pool.execute(
        """
        INSERT INTO users (tg_id, username, first_name)
        VALUES ($1, $2, $3)
        ON CONFLICT (tg_id) DO UPDATE
            SET username = EXCLUDED.username,
                first_name = EXCLUDED.first_name
        """,
        tg_id, username, first_name,
    )


async def get_user(pool: asyncpg.Pool, tg_id: int) -> asyncpg.Record | None:
    return await pool.fetchrow("SELECT * FROM users WHERE tg_id = $1", tg_id)


async def delete_user(pool: asyncpg.Pool, tg_id: int) -> bool:
    """Полностью удаляет пользователя (для теста сценария с нуля).

    Возвращает True, если запись существовала.
    """
    result = await pool.execute("DELETE FROM users WHERE tg_id = $1", tg_id)
    # asyncpg возвращает строку вида 'DELETE <n>'.
    return result.split()[-1] != "0"


async def mark_subscribed(pool: asyncpg.Pool, tg_id: int) -> None:
    await pool.execute(
        """
        UPDATE users
           SET subscribed = TRUE,
               subscribed_at = COALESCE(subscribed_at, now())
         WHERE tg_id = $1
        """,
        tg_id,
    )


async def mark_gift_sent(pool: asyncpg.Pool, tg_id: int) -> None:
    """Отмечает выдачу подарка. Останавливает дальнейшие напоминания."""
    await pool.execute(
        """
        UPDATE users
           SET gift_sent = TRUE,
               gift_sent_at = now(),
               reminders_done = TRUE
         WHERE tg_id = $1
        """,
        tg_id,
    )


async def fetch_reminder_candidates(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """Пользователи, которым ещё можно слать напоминания (не получили подарок, лимит не исчерпан)."""
    return await pool.fetch(
        """
        SELECT tg_id, created_at, reminders_sent
          FROM users
         WHERE gift_sent = FALSE
           AND reminders_done = FALSE
        """
    )


async def register_reminder(pool: asyncpg.Pool, tg_id: int, done: bool) -> None:
    """Увеличивает счётчик отправленных напоминаний; done=TRUE — лимит исчерпан."""
    await pool.execute(
        """
        UPDATE users
           SET reminders_sent = reminders_sent + 1,
               last_reminder_at = now(),
               reminders_done = $2
         WHERE tg_id = $1
        """,
        tg_id, done,
    )


async def stop_reminders(pool: asyncpg.Pool, tg_id: int) -> None:
    """Прекращает напоминания без отправки (бот заблокирован или лимит изменён)."""
    await pool.execute(
        "UPDATE users SET reminders_done = TRUE WHERE tg_id = $1", tg_id
    )


# ─────────────────────────── Настройки бота ───────────────────────────

async def get_setting(pool: asyncpg.Pool, key: str) -> str | None:
    row = await pool.fetchrow("SELECT value FROM bot_settings WHERE key = $1", key)
    return row["value"] if row else None


async def set_setting(pool: asyncpg.Pool, key: str, value: str) -> None:
    await pool.execute(
        """
        INSERT INTO bot_settings (key, value, updated_at)
        VALUES ($1, $2, now())
        ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value, updated_at = now()
        """,
        key, value,
    )


# ─────────────────────────── Лид-магнит ───────────────────────────

async def get_lead_magnet(pool: asyncpg.Pool) -> asyncpg.Record | None:
    return await pool.fetchrow("SELECT * FROM lead_magnet WHERE id = 1")


async def set_lead_magnet(
    pool: asyncpg.Pool,
    file_id: str,
    file_name: str | None,
    caption: str | None,
    mime_type: str | None,
    updated_by: int,
) -> None:
    """Заменяет текущий лид-магнит (singleton, id = 1)."""
    await pool.execute(
        """
        INSERT INTO lead_magnet (id, file_id, file_name, caption, mime_type, updated_at, updated_by)
        VALUES (1, $1, $2, $3, $4, now(), $5)
        ON CONFLICT (id) DO UPDATE
            SET file_id = EXCLUDED.file_id,
                file_name = EXCLUDED.file_name,
                caption = EXCLUDED.caption,
                mime_type = EXCLUDED.mime_type,
                updated_at = now(),
                updated_by = EXCLUDED.updated_by
        """,
        file_id, file_name, caption, mime_type, updated_by,
    )
