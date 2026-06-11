"""Расписание напоминаний: хранится в БД (изменяемо командой /setreminders),
с откатом на значение из .env (REMINDER_INTERVALS), если в БД ничего нет/битое."""
from __future__ import annotations

from datetime import timedelta

import asyncpg

from .. import repo
from ..config import parse_duration, settings

SETTING_KEY = "reminder_intervals"


def parse_intervals(raw: str) -> list[timedelta]:
    """Парсит '5m,24h,72h' в список timedelta. Бросает ValueError при ошибке/пустоте."""
    offsets = [parse_duration(x) for x in raw.split(",") if x.strip()]
    if not offsets:
        raise ValueError("Список интервалов пуст")
    return offsets


def normalize(raw: str) -> str:
    """Приводит ввод к чистому виду: '5m, 24h ,72h' -> '5m,24h,72h'."""
    return ",".join(x.strip() for x in raw.split(",") if x.strip())


async def get_reminder_intervals(pool: asyncpg.Pool) -> tuple[list[timedelta], str]:
    """Возвращает (список смещений, исходную строку). Источник: БД -> .env."""
    raw = await repo.get_setting(pool, SETTING_KEY)
    if raw:
        try:
            return parse_intervals(raw), raw
        except ValueError:
            pass  # битое значение в БД — откатываемся на .env
    return settings.reminder_offsets, settings.reminder_intervals


async def set_reminder_intervals(pool: asyncpg.Pool, raw: str) -> tuple[list[timedelta], str]:
    """Валидирует и сохраняет расписание в БД. Возвращает (смещения, нормализованную строку)."""
    clean = normalize(raw)
    offsets = parse_intervals(clean)  # бросит ValueError, если формат неверный
    await repo.set_setting(pool, SETTING_KEY, clean)
    return offsets, clean
