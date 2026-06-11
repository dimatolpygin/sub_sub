"""Конфигурация проекта. Все значения берутся из переменных окружения (.env)."""
from __future__ import annotations

import re
from datetime import timedelta

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Регэксп для разбора интервалов вида "1h", "30m", "2d".
_DURATION_RE = re.compile(r"^\s*(\d+)\s*([mhd])\s*$", re.IGNORECASE)
_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400}


def parse_duration(raw: str) -> timedelta:
    """Преобразует строку '1h' / '30m' / '2d' в timedelta."""
    match = _DURATION_RE.match(raw)
    if not match:
        raise ValueError(
            f"Некорректный интервал '{raw}'. Используйте формат вида 30m, 1h, 2d."
        )
    value, unit = int(match.group(1)), match.group(2).lower()
    return timedelta(seconds=value * _UNIT_SECONDS[unit])


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Telegram
    bot_token: str
    channel_id: str
    channel_url: str = ""
    admin_ids: str = ""

    # БД
    database_url: str
    db_schema: str = "sub_bot"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Напоминания
    reminder_intervals: str = "1h,24h,72h"
    reminder_check_interval_min: int = 5

    # Прочее
    sub_cache_ttl: int = 60
    log_level: str = "INFO"

    @field_validator("db_schema")
    @classmethod
    def _validate_schema(cls, v: str) -> str:
        # Защита от SQL-инъекции: имя схемы подставляется в DDL напрямую.
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", v):
            raise ValueError(f"Недопустимое имя схемы: {v}")
        return v

    @property
    def admin_id_list(self) -> list[int]:
        return [int(x) for x in self.admin_ids.replace(" ", "").split(",") if x]

    @property
    def reminder_offsets(self) -> list[timedelta]:
        """Список смещений от момента /start. Длина = число напоминаний."""
        return [parse_duration(x) for x in self.reminder_intervals.split(",") if x.strip()]

    @property
    def subscribe_url(self) -> str:
        """Ссылка для кнопки «Подписаться»."""
        if self.channel_url:
            return self.channel_url
        if self.channel_id.startswith("@"):
            return f"https://t.me/{self.channel_id[1:]}"
        # Числовой id без явной ссылки — кнопку-ссылку построить нельзя.
        return ""


settings = Settings()
