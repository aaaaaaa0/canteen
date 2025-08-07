import asyncio
import logging


from aiogram import Bot, Dispatcher
from bot.background_tasks import notify_all_users_loop, send_check_links_loop
from bot.handlers import router
from applications.configuration import BOT_TOKEN
from database.db_tabels import init_db


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


dp.include_router(router)


@dp.startup()
async def on_startup():
    await init_db()
    asyncio.create_task(notify_all_users_loop(bot)) 
    asyncio.create_task(send_check_links_loop(bot)) 



if __name__ == '__main__':
    try:
        asyncio.run(dp.start_polling(bot))
    except (KeyboardInterrupt, SystemExit):
        print('Бот выключен.')

  