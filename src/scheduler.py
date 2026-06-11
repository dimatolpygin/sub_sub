"""Планировщик (замена крона на APScheduler).

Каждые REMINDER_CHECK_INTERVAL_MIN минут:
  1. проверяет, кто из неподписавшихся подписался позже — и сразу выдаёт подарок;
  2. шлёт напоминания тем, у кого подошёл срок очередного напоминания.

Число напоминаний КОНЕЧНО и равно длине списка REMINDER_INTERVALS.
Смещения отсчитываются от момента /start (created_at).
"""
from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg
from redis.asyncio import Redis

from . import keyboards, repo, texts
from .config import settings
from .logger import logger
from .services.channel import get_channel_url
from .services.gift import deliver_gift
from .services.reminders_config import get_reminder_intervals
from .services.subscription import is_subscribed


async def _process_pending(bot: Bot, pool: asyncpg.Pool, redis: Redis) -> None:
    # Расписание читаем из БД (можно менять командой /setreminders без перезапуска).
    offsets, _ = await get_reminder_intervals(pool)
    max_n = len(offsets)
    now = datetime.now(timezone.utc)

    candidates = await repo.fetch_reminder_candidates(pool)
    if not candidates:
        return

    logger.debug(f"Планировщик: проверяю {len(candidates)} пользователей")
    channel_url = await get_channel_url(bot)

    for row in candidates:
        tg_id = row["tg_id"]
        sent = row["reminders_sent"]

        # Лимит исчерпан (например, список интервалов укоротили) — больше не беспокоим.
        if sent >= max_n:
            await repo.stop_reminders(pool, tg_id)
            continue

        # Пора ли слать очередное напоминание? Срок = created_at + offsets[sent].
        due_at = row["created_at"] + offsets[sent]
        if now < due_at:
            continue

        # Сначала проверяем: вдруг человек уже подписался (без нажатия кнопки).
        if await is_subscribed(bot, redis, tg_id, use_cache=True):
            await repo.mark_subscribed(pool, tg_id)
            if await deliver_gift(bot, pool, tg_id):
                logger.info(f"🎁→ Планировщик выдал подарок подписавшемуся user_id={tg_id}")
            continue

        # Не подписан — шлём напоминание.
        is_last = (sent + 1) >= max_n
        try:
            await bot.send_message(
                tg_id,
                texts.REMINDER,
                reply_markup=keyboards.subscribe_kb(channel_url),
            )
            await repo.register_reminder(pool, tg_id, done=is_last)
            logger.info(
                f"🔔→ Напоминание #{sent + 1}/{max_n} отправлено user_id={tg_id}"
                + (" (последнее)" if is_last else "")
            )
        except TelegramForbiddenError:
            # Пользователь заблокировал бота — прекращаем попытки.
            await repo.stop_reminders(pool, tg_id)
            logger.warning(f"user_id={tg_id} заблокировал бота — напоминания остановлены")
        except TelegramAPIError as e:
            logger.error(f"Ошибка отправки напоминания user_id={tg_id}: {e}")


def start_scheduler(bot: Bot, pool: asyncpg.Pool, redis: Redis) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _process_pending,
        trigger="interval",
        minutes=settings.reminder_check_interval_min,
        args=(bot, pool, redis),
        id="process_pending",
        next_run_time=datetime.now(timezone.utc),  # первый прогон сразу после старта
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        f"✅ Планировщик запущен: проверка каждые {settings.reminder_check_interval_min} мин. "
        f"Расписание по умолчанию: {settings.reminder_intervals} "
        f"(меняется командой /setreminders, хранится в БД)"
    )
    return scheduler
