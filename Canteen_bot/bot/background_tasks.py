import logging
import asyncio


from aiogram import  Bot
from sqlalchemy import select, update
from database.db_tabels import async_session, Order,User


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# Для уведомления польщователя о ссылке для оплаты заказ (первое уведомление, автоматически)
async def send_check_links_loop(bot: Bot):
    while True:
        async with async_session() as session:
            stmt = select(Order).where(
                Order.checks.isnot(None),
                Order.check_sent == False
            )
            result = await session.execute(stmt)
            orders = result.scalars().all()
            for order in orders:
                user_stmt = select(User.tg_id).where(User.id == order.user_id)
                user_result = await session.execute(user_stmt)
                tg_id = user_result.scalar_one_or_none()
                if tg_id is None:
                    print(f"Не найден tg_id для user_id {order.user_id}")
                    continue
                try:
                    await bot.send_message(
                        chat_id=tg_id,
                        text=f"Ваша ссылка для оплаты заказа №{order.id}: {order.total_price}₽\n\n{order.checks}"
                    )
                    await session.execute(
                        update(Order)
                        .where(Order.id == order.id)
                        .values(check_sent=True)
                    )
                except Exception as e:
                    print(f"Ошибка при отправке чека пользователю {order.user_id}: {e}")
            await session.commit()
        await asyncio.sleep(10)


# Для уведомления пользователя о ссылке для оплаты заказа (отправлено одамином вручную)
async def notify_all_users_loop(bot: Bot):
    while True:
        async with async_session() as session:
            stmt = select(Order).where(Order.notification == True)
            result = await session.execute(stmt)
            orders = result.scalars().all()
            for order in orders:
                if order.checks:  
                    tg_id_stmt = select(User.tg_id).where(User.id == order.user_id)
                    tg_id_result = await session.execute(tg_id_stmt)
                    tg_id = tg_id_result.scalar_one_or_none()
                    if tg_id:
                        try:
                            await bot.send_message(chat_id=tg_id,text=f"Ваша ссылка для оплаты заказа №{order.id}: {order.total_price}₽\n\n{order.checks}")
                            await session.execute(
                                update(Order)
                                .where(Order.id == order.id)
                                .values(notification=False)
                            )
                        except Exception as e:
                            print(f"Ошибка при отправке уведомления пользователю {tg_id}: {e}")
                    else:
                        print(f"tg_id не найден для user_id {order.user_id}")
            await session.commit()
        await asyncio.sleep(10)