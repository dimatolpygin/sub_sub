"""Inline-клавиатуры."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import settings

CHECK_CALLBACK = "check_sub"


def subscribe_kb() -> InlineKeyboardMarkup:
    """Кнопка перехода в канал (если есть ссылка) + кнопка проверки подписки."""
    builder = InlineKeyboardBuilder()
    if settings.subscribe_url:
        builder.row(
            InlineKeyboardButton(text="Подписаться на канал", url=settings.subscribe_url)
        )
    builder.row(
        InlineKeyboardButton(text="Я подписался", callback_data=CHECK_CALLBACK)
    )
    return builder.as_markup()
