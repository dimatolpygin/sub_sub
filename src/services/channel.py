"""Получение ссылки на канал для кнопки «Подписаться».

Если CHANNEL_ID — числовой id, ссылку из него не собрать, поэтому спрашиваем у
Telegram (бот должен быть админом канала): берём публичный username либо
существующую/новую invite-ссылку. Результат кешируется в памяти на время работы.
"""
from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from ..config import settings
from ..logger import logger

_cached_url: str | None = None


async def get_channel_url(bot: Bot) -> str:
    """Возвращает ссылку на канал (или пустую строку, если получить не удалось)."""
    global _cached_url
    if _cached_url is not None:
        return _cached_url

    # 1. Явно задан в .env — приоритет.
    if settings.channel_url:
        _cached_url = settings.channel_url
        return _cached_url

    # 2. CHANNEL_ID в виде @username — ссылка собирается напрямую.
    if settings.channel_id.startswith("@"):
        _cached_url = f"https://t.me/{settings.channel_id[1:]}"
        return _cached_url

    # 3. Числовой id — спрашиваем у Telegram.
    try:
        chat = await bot.get_chat(settings.channel_id)
        if chat.username:
            _cached_url = f"https://t.me/{chat.username}"
        elif chat.invite_link:
            _cached_url = chat.invite_link
        else:
            link = await bot.create_chat_invite_link(settings.channel_id)
            _cached_url = link.invite_link
        logger.info(f"Ссылка на канал определена: {_cached_url}")
    except TelegramAPIError as e:
        logger.error(
            f"Не удалось получить ссылку на канал {settings.channel_id}: {e}. "
            f"Проверьте, что бот — администратор канала, или задайте CHANNEL_URL в .env."
        )
        _cached_url = ""

    return _cached_url
