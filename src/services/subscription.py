"""Проверка подписки пользователя на канал. Результат кешируется в Redis."""
from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from redis.asyncio import Redis

from ..config import settings
from ..logger import logger

# Статусы, которые считаем «подписан».
_SUBSCRIBED_STATUSES = {"creator", "administrator", "member", "restricted"}


async def is_subscribed(bot: Bot, redis: Redis, user_id: int, use_cache: bool = True) -> bool:
    """Проверяет членство пользователя в канале CHANNEL_ID.

    Кеш в Redis (TTL = SUB_CACHE_TTL) защищает от частого дёргания Telegram API.
    При нажатии кнопки «Я подписался» кеш стоит обходить (use_cache=False),
    чтобы увидеть свежий статус.
    """
    cache_key = f"sub:{user_id}"

    if use_cache:
        cached = await redis.get(cache_key)
        if cached is not None:
            return cached == "1"

    try:
        member = await bot.get_chat_member(settings.channel_id, user_id)
        status = member.status
        subscribed = status in _SUBSCRIBED_STATUSES
        # 'restricted' считается подпиской только если пользователь всё ещё участник.
        if status == "restricted":
            subscribed = bool(getattr(member, "is_member", False))
    except TelegramAPIError as e:
        # Частая причина: бот не админ канала или неверный CHANNEL_ID.
        logger.error(f"Не удалось проверить подписку user_id={user_id}: {e}")
        return False

    await redis.set(cache_key, "1" if subscribed else "0", ex=settings.sub_cache_ttl)
    return subscribed
