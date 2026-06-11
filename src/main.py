"""Точка входа: инициализация БД/Redis, миграции, запуск бота (polling)."""
from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from .cache import close_redis, init_redis
from .config import settings
from .db import close_pool, init_pool
from .handlers import get_main_router
from .logger import setup_logging
from .middlewares import LoggingMiddleware
from .migrator import apply_migrations
from .scheduler import start_scheduler


async def main() -> None:
    log = setup_logging(settings.log_level)
    log.info("⏳ Запуск бота лид-магнита...")

    # Инфраструктура.
    pool = await init_pool()
    await apply_migrations(pool)
    redis = await init_redis()

    # Бот и диспетчер. FSM-состояния храним в Redis.
    storage = RedisStorage.from_url(settings.redis_url)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Зависимости, доступные во всех хендлерах как аргументы pool / redis.
    dp["pool"] = pool
    dp["redis"] = redis

    dp.update.middleware(LoggingMiddleware())
    dp.include_router(get_main_router())

    # Планировщик напоминаний и проверки подписок.
    scheduler = start_scheduler(bot, pool, redis)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        me = await bot.get_me()
        log.info(f"✅ Бот @{me.username} запущен (режим: polling)")
        await dp.start_polling(bot)
    finally:
        log.info("Останавливаю бота...")
        scheduler.shutdown(wait=False)
        await close_redis()
        await close_pool()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
