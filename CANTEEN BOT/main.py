import asyncio
from aiogram import Bot, Dispatcher

from bot.handlers import router
from applications.configuration import BOT_TOKEN
from database.db_tabels import init_db

import logging

logging.basicConfig(
    level=logging.DEBUG,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print('Бот выключен.')
