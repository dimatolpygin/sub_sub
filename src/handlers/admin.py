"""Админские хендлеры: замена файла лид-магнита (/setfile)."""
from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter, Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.text_decorations import html_decoration
import asyncpg
from redis.asyncio import Redis

from .. import repo, texts
from ..config import settings
from ..logger import logger
from ..services.reminders_config import get_reminder_intervals, set_reminder_intervals

router = Router()


class AdminFilter(BaseFilter):
    """Пропускает только пользователей из ADMIN_IDS."""

    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id in settings.admin_id_list


class SetFile(StatesGroup):
    waiting_for_file = State()


@router.message(Command("admin"), AdminFilter())
async def cmd_admin(message: Message) -> None:
    await message.answer(texts.ADMIN_HELP)


# Если не-админ зовёт /admin — мягко отказываем.
@router.message(Command("admin"))
async def cmd_admin_denied(message: Message) -> None:
    await message.answer(texts.ADMIN_ONLY)


@router.message(Command("setfile"), AdminFilter())
async def cmd_setfile(message: Message, state: FSMContext) -> None:
    await state.set_state(SetFile.waiting_for_file)
    await message.answer(texts.ADMIN_SETFILE_PROMPT)
    logger.info(f"🛠 Админ id={message.from_user.id} начал замену лид-магнита")


# Если не-админ зовёт /setfile — мягко отказываем.
@router.message(Command("setfile"))
async def cmd_setfile_denied(message: Message) -> None:
    await message.answer(texts.ADMIN_ONLY)


@router.message(Command("reset"), AdminFilter())
async def cmd_reset(
    message: Message, command: CommandObject, pool: asyncpg.Pool, redis: Redis
) -> None:
    """Сброс пользователя для повторного теста сценария с нуля.

    /reset           — сбросить себя
    /reset 12345     — сбросить пользователя по id
    """
    target = message.from_user.id
    other = False
    if command.args:
        arg = command.args.strip()
        if not arg.lstrip("-").isdigit():
            await message.answer(texts.ADMIN_RESET_USAGE)
            return
        target = int(arg)
        other = target != message.from_user.id

    existed = await repo.delete_user(pool, target)
    # Сбрасываем и кеш проверки подписки, чтобы статус перепроверился сразу.
    await redis.delete(f"sub:{target}")

    if other:
        text = texts.ADMIN_RESET_OTHER if existed else texts.ADMIN_RESET_NOT_FOUND
        await message.answer(text.format(id=target))
    else:
        await message.answer(texts.ADMIN_RESET_SELF)
    logger.info(f"🛠 Сброс пользователя id={target} админом id={message.from_user.id}")


# Если не-админ зовёт /reset — мягко отказываем.
@router.message(Command("reset"))
async def cmd_reset_denied(message: Message) -> None:
    await message.answer(texts.ADMIN_ONLY)


@router.message(Command("setreminders"), AdminFilter())
async def cmd_setreminders(
    message: Message, command: CommandObject, pool: asyncpg.Pool
) -> None:
    """Показать/изменить расписание напоминаний.

    /setreminders             — показать текущее
    /setreminders 5m,24h,72h  — задать новое (применяется сразу)
    """
    if not command.args:
        offsets, raw = await get_reminder_intervals(pool)
        await message.answer(
            texts.ADMIN_REMINDERS_CURRENT.format(value=escape(raw), count=len(offsets))
        )
        return

    try:
        offsets, clean = await set_reminder_intervals(pool, command.args)
    except ValueError:
        await message.answer(texts.ADMIN_REMINDERS_BAD)
        return

    await message.answer(
        texts.ADMIN_REMINDERS_OK.format(value=escape(clean), count=len(offsets))
    )
    logger.info(
        f"🛠 Расписание напоминаний изменено на '{clean}' админом id={message.from_user.id}"
    )


# Если не-админ зовёт /setreminders — мягко отказываем.
@router.message(Command("setreminders"))
async def cmd_setreminders_denied(message: Message) -> None:
    await message.answer(texts.ADMIN_ONLY)


@router.message(Command("cancel"), StateFilter(SetFile.waiting_for_file))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.ADMIN_CANCELLED)


@router.message(StateFilter(SetFile.waiting_for_file), F.document)
async def receive_file(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    doc = message.document
    # Сохраняем подпись с форматированием: рендерим entities в HTML (с экранированием).
    caption_html = (
        html_decoration.unparse(message.caption, message.caption_entities or [])
        if message.caption
        else None
    )
    await repo.set_lead_magnet(
        pool,
        file_id=doc.file_id,
        file_name=doc.file_name,
        caption=caption_html,
        mime_type=doc.mime_type,
        updated_by=message.from_user.id,
    )
    await state.clear()
    await message.answer(texts.ADMIN_SETFILE_OK.format(name=escape(doc.file_name or "файл")))
    logger.info(
        f"🛠 Лид-магнит обновлён: {doc.file_name} (file_id={doc.file_id}) "
        f"админом id={message.from_user.id}"
    )


# В состоянии ожидания пришло что-то кроме документа.
@router.message(StateFilter(SetFile.waiting_for_file))
async def receive_not_a_doc(message: Message) -> None:
    await message.answer(texts.ADMIN_SETFILE_NOT_A_DOC)
