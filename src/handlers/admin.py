"""Админские хендлеры: замена файла лид-магнита (/setfile)."""
from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.text_decorations import html_decoration
import asyncpg

from .. import repo, texts
from ..config import settings
from ..logger import logger

router = Router()


class AdminFilter(BaseFilter):
    """Пропускает только пользователей из ADMIN_IDS."""

    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id in settings.admin_id_list


class SetFile(StatesGroup):
    waiting_for_file = State()


@router.message(Command("setfile"), AdminFilter())
async def cmd_setfile(message: Message, state: FSMContext) -> None:
    await state.set_state(SetFile.waiting_for_file)
    await message.answer(texts.ADMIN_SETFILE_PROMPT)
    logger.info(f"🛠 Админ id={message.from_user.id} начал замену лид-магнита")


# Если не-админ зовёт /setfile — мягко отказываем.
@router.message(Command("setfile"))
async def cmd_setfile_denied(message: Message) -> None:
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
