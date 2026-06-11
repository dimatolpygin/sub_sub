"""Сбор всех роутеров."""
from aiogram import Router

from . import admin, start


def get_main_router() -> Router:
    router = Router()
    # Админские хендлеры регистрируем первыми (более специфичные фильтры).
    router.include_router(admin.router)
    router.include_router(start.router)
    return router
