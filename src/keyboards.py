"""Inline-клавиатуры."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

CHECK_CALLBACK = "check_sub"


def subscribe_kb(channel_url: str = "") -> InlineKeyboardMarkup:
    """Кнопка перехода в канал (если есть ссылка) + кнопка проверки подписки."""
    builder = InlineKeyboardBuilder()
    if channel_url:
        builder.row(
            InlineKeyboardButton(text="Подписаться на канал", url=channel_url)
        )
    builder.row(
        InlineKeyboardButton(text="Я подписался", callback_data=CHECK_CALLBACK)
    )
    return builder.as_markup()
