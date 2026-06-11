"""Middleware сквозного логирования действий пользователей (для отладки в терминале)."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from .logger import logger


class LoggingMiddleware(BaseMiddleware):
    """Логирует каждое входящее сообщение и нажатие inline-кнопки."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update: Update = event  # type: ignore[assignment]

        if update.message is not None:
            self._log_message(update.message)
        elif update.callback_query is not None:
            self._log_callback(update.callback_query)

        return await handler(event, data)

    @staticmethod
    def _log_message(msg: Message) -> None:
        u = msg.from_user
        if u is None:
            return
        if msg.document is not None:
            text = f"(документ: {msg.document.file_name})"
        else:
            text = msg.text or "(медиа)"
        logger.info(
            f"👤 @{u.username or '—'} (id:{u.id}, {u.first_name}) → {text}"
        )

    @staticmethod
    def _log_callback(cb: CallbackQuery) -> None:
        u = cb.from_user
        logger.info(
            f"👤 @{u.username or '—'} (id:{u.id}, {u.first_name}) → [кнопка] {cb.data}"
        )
