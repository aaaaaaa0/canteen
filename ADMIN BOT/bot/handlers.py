from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from database.db_tabels import async_session, Order, Cart, Product, User, Menu_Section, Admin
import database.db_requests as rq
import bot.keyboards as kb
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

router = Router()


# ====================================================================
# COMMANDS
# ====================================================================

@router.message(Command("start"))
async def cmd_start(message: Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id  

    await rq.set_admin(tg_id=tg_id, chat_id=chat_id)
    await message.answer(
        "Здравствуйте! Я бот для управления заказами. Вы можете использовать команды для взаимодействия со мной.",
        reply_markup=kb.main_keyboard
    )




# ====================================================================
# HANDLERS
# ====================================================================
async def get_admin_chat_ids() -> list[int]:
    async with async_session() as session:
        result = await session.execute(select(Admin.chat_id))
        chat_ids = [row[0] for row in result.fetchall()]
        return chat_ids

# УВЕДОМЛЕНИЕ АДМИНИСТРАТОРАМ О НОВОМ ЗАКАЗЕ
async def notify_admins_about_order(order_id: int, bot: Bot):
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return

        user = await session.get(User, order.user_id)
        if not user:
            return

        result = await session.execute(
            select(Cart).where(Cart.order_id == order_id)
        )
        cart_items = result.scalars().all()
        if not cart_items:
            return

        cold_section_result = await session.execute(
            select(Menu_Section.id).where(Menu_Section.name == "Холодные закуски")
        )
        cold_section_id = cold_section_result.scalar()

        cold_dishes = []
        other_dishes = []

        for item in cart_items:
            product = await session.get(Product, item.product_id)
            if not product:
                continue

            line = f"• {product.name} × {item.quantity}"

            if product.menu_section_id == cold_section_id:
                cold_dishes.append(line)
            else:
                other_dishes.append(line)

        text = (
            f"🆕 <b>Новый заказ</b>\n\n"
            f"<b>ФИО:</b> {order.name or user.name}\n"
            f"<b>Телефон:</b> {order.phone or user.phone}\n"
            f"<b>Адрес:</b> {order.address or user.address}\n\n"
            f"<b>Холодные закуски:</b>\n" + ("\n".join(cold_dishes) if cold_dishes else "—") + "\n\n"
            f"<b>Другие блюда:</b>\n" + ("\n".join(other_dishes) if other_dishes else "—") + "\n\n"
            f"<b>Вилки:</b> {order.forks or 0} шт.\n"
            f"<b>Ложки:</b> {order.spoons or 0} шт."
        )

        result = await session.execute(select(Admin.tg_id))
        admin_ids = result.scalars().all()

        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception as e:
                print(f"Не удалось отправить сообщение админу {admin_id}: {e}")
