"""Выдача подарка (лид-магнита). Используется и в хендлерах, и в планировщике."""
from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile  # noqa: F401  (на будущее, если файл из ФС)
import asyncpg

from .. import repo, texts
from ..logger import logger


async def deliver_gift(bot: Bot, pool: asyncpg.Pool, user_id: int) -> bool:
    """Отправляет пользователю файл-подарок и помечает выдачу в БД.

    Возвращает True, если подарок реально отправлен.
    """
    lm = await repo.get_lead_magnet(pool)
    if lm is None:
        logger.warning(
            f"Подарок не настроен (lead_magnet пуст). Пользователь user_id={user_id} ждёт файл."
        )
        try:
            await bot.send_message(user_id, texts.GIFT_NOT_CONFIGURED_USER)
        except TelegramAPIError:
            pass
        return False

    caption = lm["caption"] or texts.GIFT_CAPTION_FALLBACK
    try:
        await bot.send_document(user_id, document=lm["file_id"], caption=caption)
    except TelegramAPIError as e:
        logger.error(f"Не удалось отправить подарок user_id={user_id}: {e}")
        return False

    await repo.mark_gift_sent(pool, user_id)
    logger.info(f"🎁→ Подарок отправлен user_id={user_id} (файл: {lm['file_name']})")
    return True
