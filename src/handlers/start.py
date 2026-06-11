"""Хендлеры пользователя: /start, проверка подписки, выдача подарка."""
from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
import asyncpg
from redis.asyncio import Redis

from .. import keyboards, repo, texts
from ..logger import logger
from ..services.channel import get_channel_url
from ..services.gift import deliver_gift
from ..services.subscription import is_subscribed

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, pool: asyncpg.Pool, redis: Redis) -> None:
    u = message.from_user
    await repo.upsert_user(pool, u.id, u.username, u.first_name)

    if await is_subscribed(bot, redis, u.id, use_cache=False):
        # Уже подписан — сразу выдаём файл, без лишних сообщений.
        await repo.mark_subscribed(pool, u.id)
        await deliver_gift(bot, pool, u.id)
        logger.info(f"🤖 Бот → @{u.username or '—'}: выдан подарок (уже подписан)")
    else:
        await message.answer(
            texts.START_NOT_SUBSCRIBED.format(name=escape(u.first_name or "друг")),
            reply_markup=keyboards.subscribe_kb(await get_channel_url(bot)),
        )
        logger.info(f"🤖 Бот → @{u.username or '—'}: предложена подписка")


@router.callback_query(F.data == keyboards.CHECK_CALLBACK)
async def cb_check_sub(
    callback: CallbackQuery, bot: Bot, pool: asyncpg.Pool, redis: Redis
) -> None:
    u = callback.from_user

    if await is_subscribed(bot, redis, u.id, use_cache=False):
        await repo.mark_subscribed(pool, u.id)
        # Короткое уведомление-«тост», в чат пишем только сам файл.
        await callback.answer(texts.GIFT_TOAST)
        # Убираем кнопки, чтобы не нажимали повторно.
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:  # сообщение могло устареть — не критично
            pass
        await deliver_gift(bot, pool, u.id)
        logger.info(f"🤖 Бот → @{u.username or '—'}: выдан подарок (после проверки)")
    else:
        await callback.answer(texts.NOT_SUBSCRIBED_YET, show_alert=True)
        logger.info(f"🤖 Бот → @{u.username or '—'}: подписка не найдена")
