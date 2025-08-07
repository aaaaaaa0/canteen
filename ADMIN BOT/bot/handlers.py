from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select, update
from datetime import time
from database.db_tabels import async_session, Order, Cart, Product, User, Menu_Section, Admin, WorkTime
from bot.keyboards import work_time_keyboard
from applications.configuration import BOT_TOKEN

import database.db_requests as rq
import bot.keyboards as kb
import asyncio
import logging


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


router = Router()
bot = Bot(token=BOT_TOKEN)


# ====================================================================
# КОМАНДЫ
# ====================================================================


# Команда /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id  
    await rq.set_admin(tg_id=tg_id, chat_id=chat_id)
    await message.answer(
        "Здравствуйте! Я бот для управления заказами. Вы можете использовать меню для взаимодействия со мной.",
        reply_markup=kb.main_keyboard
    )


# ====================================================================
# УВЕДОМЛЕНИЯ О НОВЫХ ЗАКАЗАХ
# ====================================================================


# Получить id админа 
async def get_admin_chat_ids() -> list[int]:
    async with async_session() as session:
        result = await session.execute(select(Admin.chat_id))
        chat_ids = [row[0] for row in result.fetchall()]
        return chat_ids


# Уведомление админов о новом заказе
async def notify_admins_about_order(order_id: int, bot: Bot):
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return
        user = await session.get(User, order.user_id)
        if not user:
            return
        result = await session.execute(
            select(Cart)
            .where(Cart.order_id == order_id))
        cart_items = result.scalars().all()
        if not cart_items:
            return
        cold_section_result = await session.execute(
            select(Menu_Section.id)
            .where(Menu_Section.name == "Холодные закуски"))
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
            f"<b>ID заказа:</b>  {order.id}\n"
            f"<b>ФИО:</b>  {order.name}\n"
            f"<b>Телефон:</b>  {order.phone}\n"
            f"<b>Адрес:</b>  {order.address}\n\n"
            f"<b>Холодные закуски:</b>\n" + ("\n".join(cold_dishes) if cold_dishes else "—") + "\n\n"
            f"<b>Другие блюда:</b>\n" + ("\n".join(other_dishes) if other_dishes else "—") + "\n\n"
            f"<b>Вилки:</b>  {order.forks or 0} шт.\n"
            f"<b>Ложки:</b>  {order.spoons or 0} шт."
        )
        result = await session.execute(select(Admin.tg_id))
        admin_ids = result.scalars().all()
        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception as e:
                print(f"Не удалось отправить сообщение админу {admin_id}: {e}")


# ====================================================================
# ДОБАВЛЕНИЕ ССЫЛКИ ДЛЯ ОПЛАТЫ ЗАКАЗОВ
# ====================================================================


# Состояния для добавления ссылки для оплаты
class AddCheckStates(StatesGroup):
    choosing_order_id = State()
    confirming_order = State()
    entering_check_url = State()


# Обработка кнопки [Добавить ссылку для оплаты заказа]
@router.message(F.text == "Добавить ссылку для оплаты заказа")
async def start_add_check(message: types.Message, state: FSMContext):
    async with async_session() as session:
        stmt = (
            select(Order.id, Order.name, Order.created_at, Order.total_price)
            .where(Order.checks == None)
            .order_by(Order.created_at.desc())
        )
        result = await session.execute(stmt)
        orders = result.fetchall()
        if not orders:
            await message.answer("Все заказы уже содержат чек.")
            return
        text = "Введите ID заказа для добавления ссылки:\n\n"
        for order in orders:
            order_id, name, created_at, total_price = order
            text += f"{order_id}: {name},  {created_at},  {total_price} ₽\n"
        await message.answer(text)
        await state.set_state(AddCheckStates.choosing_order_id)


# Обработка ввода ID заказа для добавления ссылки
@router.message(AddCheckStates.choosing_order_id)
async def receive_order_id(message: types.Message, state: FSMContext):
    try:
        order_id = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
        return
    async with async_session() as session:
        stmt = select(Order).where(Order.id == order_id, Order.checks == None)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            await message.answer("Такого заказа без чека не найдено.")
            return
        await state.update_data(order_id=order_id)
        text = (
            f"<b>ID заказа:</b>  {order.id}\n\n"
            f"<b>Дата:</b>  {order.created_at}\n"
            f"<b>ФИО:</b>  {order.name}\n"
            f"<b>Тел:</b>  {order.phone}\n"
            f"<b>Адрес:</b>  {order.address}\n\n"
            f"<b>Стоимость:</b>  {order.total_price} ₽"
        )
        keyboard = kb.add_check_kb 
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(AddCheckStates.confirming_order)


# Обработка кнопки [ДОБАВИТЬ ССЫЛКУ]
@router.callback_query(F.data == "confirm_order_check", AddCheckStates.confirming_order)
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Отправьте ссылку для оплаты заказа.")
    await state.set_state(AddCheckStates.entering_check_url)


# Обработка ввода ссылки для оплаты
@router.message(AddCheckStates.entering_check_url)
async def receive_check_url(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data["order_id"]
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("Пожалуйста, отправьте корректную ссылку, начинающуюся с http.")
        return
    async with async_session() as session:
        stmt = select(Order).where(Order.id == order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order:
            order.checks = url
            await session.commit()
            await message.answer(f"Ссылка на оплату для заказа сохранена.\n\nID заказа: {order.id}")
        else:
            await message.answer("Ошибка: заказ не найден.")
    await state.clear()


# ====================================================================
# УДАЛИТЬ ССЫЛКИ ДЛЯ ОПЛАТЫ ЗАКАЗОВ
# ====================================================================


# Cостояния для удаления ссылки для оплаты
class RemoveCheckStates(StatesGroup):
    choosing_order_id = State()
    confirming_deletion = State()


# Обработка кнопки [Удалить ссылку для оплаты заказа]
@router.message(F.text == "Удалить ссылку для оплаты заказа")
async def start_remove_check(message: types.Message, state: FSMContext):
    await message.answer("Введите ID заказа для удаления ссылки.")
    await state.set_state(RemoveCheckStates.choosing_order_id)


# Обработка ввода ID заказа для удаления ссылки
@router.message(RemoveCheckStates.choosing_order_id)
async def receive_order_id_for_deletion(message: types.Message, state: FSMContext):
    try:
        order_id = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
        return
    async with async_session() as session:
        stmt = select(Order).where(Order.id == order_id, Order.checks != None)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            await message.answer("Такого заказа с ссылкой не найдено.")
            return
        await state.update_data(order_id=order_id)
        text = (
            f"<b>ID заказа:</b>  {order.id}\n\n"
            f"<b>Дата:</b>  {order.created_at}\n"
            f"<b>ФИО:</b>  {order.name}\n"
            f"<b>Телефон:</b>  {order.phone}\n"
            f"<b>Адрес:</b>  {order.address}\n\n"
            f"<b>Стоимость:</b>  {order.total_price} ₽\n"
            f"<b>Ccылка:</b>  {order.checks}\n"
        )
        keyboard = kb.del_check_kb 
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(RemoveCheckStates.confirming_deletion)


# Обработка кнопки [УДАЛИТЬ ССЫЛКУ]
@router.callback_query(F.data == "confirm_delete_check", RemoveCheckStates.confirming_deletion)
async def confirm_delete(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_id = data["order_id"]
    async with async_session() as session:
        stmt = select(Order).where(Order.id == order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order:
            order.checks = None
            await session.commit()
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(f"Ссылка для оплаты заказа удалена.\n\nID заказа: {order.id}")
        else:
            await callback.message.answer("Ошибка: заказ не найден.")
    await state.clear()


# ====================================================================
# ВРЕМЯ ПРИЁМА ЗАКАЗОВ
# ====================================================================


# Функция для форматирования строки времени
def parse_time_string(input_str: str) -> tuple[int, int] | None:
    digits = ''.join(filter(str.isdigit, input_str))
    if len(digits) != 4:
        return None
    h, m = int(digits[:2]), int(digits[2:])
    if 0 <= h < 24 and 0 <= m < 60:
        return h, m
    return None


# Состояния для редактирования времени и остановки
class EditWorkTime(StatesGroup):
    waiting_for_new_start = State()
    waiting_for_new_end = State()


# Обработка кнопки [Время приёма заказов]
@router.message(F.text == "Время приёма заказов")
async def show_work_time(message: types.Message):
    async with async_session() as session:
        result = await session.execute(select(WorkTime).where(WorkTime.id == 1))
        time_data = result.scalar_one()
        start = time_data.start.strftime("%H:%M")
        end = time_data.end.strftime("%H:%M")
        stop = time_data.stop
        stop_status = ("Приём заказов ВКЛЮЧЁН (True)\n\nБот для приёма заказов работает по заданному расписанию."
                       if stop else "Приём заказов ОСТАНОВЛЕН (False)")
        await message.answer(
            f"Время приёма заказов:\n\n"
            f"Начало:  {start}\n"
            f"Окончание:  {end}\n"
            f"Стоп:  {stop_status}",
            reply_markup=work_time_keyboard()
        )


# Обработка кнопки [ИЗМЕНИТЬ НАЧАЛО]
@router.callback_query(F.data == "change_start")
async def ask_new_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое время начала приёма заказов.\n\nФормат: ЧЧ MM")
    await state.set_state(EditWorkTime.waiting_for_new_start)
    await callback.answer()


# Обработка кнопки [ИЗМЕНИТЬ ОКОНЧАНИЕ]
@router.callback_query(F.data == "change_end")
async def ask_new_end(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое время окончания приёма заказов.\n\nФормат: ЧЧ ММ")
    await state.set_state(EditWorkTime.waiting_for_new_end)
    await callback.answer()


# Обработка кнопки [ВКЛ\ВЫКЛ ПРИЁМ ЗАКАЗОВ]
@router.callback_query(F.data == "toggle_stop")
async def toggle_stop(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(WorkTime).where(WorkTime.id == 1))
        time_data = result.scalar_one()
        new_stop = not time_data.stop
        time_data.stop = new_stop
        await session.commit()
        status = "включён" if new_stop else "остановлен"
        await callback.message.answer(f"Приём заказов {status.upper()}.")
    await show_work_time(callback.message)
    await callback.answer()


# Обновление времени начала приёма заказов
@router.message(EditWorkTime.waiting_for_new_start)
async def set_new_start(message: types.Message, state: FSMContext):
    parsed = parse_time_string(message.text)
    if not parsed:
        await message.answer("Неверный формат.\n\nПримеры правильного: 0930, 09:30, 09-30, 09 30 → 09:30.")
        return
    h, m = parsed
    new_start = time(hour=h, minute=m)
    async with async_session() as session:
        result = await session.execute(select(WorkTime).where(WorkTime.id == 1))
        work_time = result.scalar_one_or_none()
        if not work_time:
            await message.answer("Ошибка: расписание не инициализировано.")
            await state.clear()
            return
        current_end: time = work_time.end
        if not (new_start < current_end):
            await message.answer(f"Неверно: время начала ({new_start.strftime('%H:%M')}) должно быть позднее окончания ({current_end.strftime('%H:%M')}).")
            return
        await session.execute(
            update(WorkTime)
            .where(WorkTime.id == 1)
            .values(start=new_start)
            )
        await session.commit()
        await message.answer(f"Время начала обновлено: {new_start.strftime('%H:%M')}")
        await show_work_time(message)
    await state.clear()


# Обновление времени окончания приёма заказов
@router.message(EditWorkTime.waiting_for_new_end)
async def set_new_end(message: types.Message, state: FSMContext):
    parsed = parse_time_string(message.text)
    if not parsed:
        await message.answer("Неверный формат.\n\nПримеры правильного: 1130, 11:30, 11-30, 11 30 → 11:30.")
        return
    h, m = parsed
    new_end = time(hour=h, minute=m)
    async with async_session() as session:
        result = await session.execute(select(WorkTime).where(WorkTime.id == 1))
        work_time = result.scalar_one_or_none()
        if not work_time:
            await message.answer("Ошибка: расписание не инициализировано.")
            await state.clear()
            return
        current_start: time = work_time.start
        if not (current_start < new_end):
            await message.answer(f"Неверно: время окончания ({new_end.strftime('%H:%M')}) должно быть раньше начала ({current_start.strftime('%H:%M')}).")
            return
        await session.execute(
            update(WorkTime)
            .where(WorkTime.id == 1)
            .values(end=new_end)
            )
        await session.commit()
        await message.answer(f"Время окончания обновлено: {new_end.strftime('%H:%M')}")
        await show_work_time(message)
    await state.clear()


# ====================================================================
# ОТПРАВКА ССЫЛКИ НА ОПЛАТУ
# ====================================================================


# Состояния для отправки уведомления
class NotifyStates(StatesGroup):
    waiting_for_order_id = State()
    confirming = State()


# Обработка кнопки [Уведомить о новой ссылке для оплаты]
@router.message(F.text== "Уведомить о новой ссылке для оплаты")
async def start_notify(message: types.Message, state: FSMContext):
    await message.answer("Введите ID заказа:")
    await state.set_state(NotifyStates.waiting_for_order_id)


# Получение ID заказа
@router.message(NotifyStates.waiting_for_order_id)
async def receive_order_id(message: types.Message, state: FSMContext):
    try:
        order_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите корректный числовой ID заказа.")
        return
    async with async_session() as session:
        stmt = select(Order).where(Order.id == order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            await message.answer("Заказ не найден.")
            return
        await state.update_data(order_id=order_id)
        info = (
            f"<b>ID заказа:</b>  {order.id}\n\n"
            f"<b>ФИО:</b>  {order.name}\n"
            f"<b>Тел:</b>  {order.phone}\n"
            f"<b>Адрес:</b>  {order.address}\n\n"
            f"<b>Стоимость:</b>  {order.total_price} р.\n"
            f"<b>Ссылка:</b>  {order.checks or 'нет'}"
        )
        keyboard = kb.notify_check_kb
        await message.answer(info,  parse_mode="HTML",reply_markup=keyboard)
        await state.set_state(NotifyStates.confirming)


# Обработка подтверждения отправки уведомления
@router.callback_query(F.data == "confirm_notify", NotifyStates.confirming)
async def confirm_notify(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    data = await state.get_data()
    order_id = data.get("order_id")
    async with async_session() as session:
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(notification=True)
            )
        await session.commit()
    await callback.message.answer(f"Сcылка для оплаты заказа отправлена.\n\nID заказа: {order_id}.")
    await state.clear()
    asyncio.create_task(reset_notification_after_delay(order_id))


# Сброс уведомления через минуту
async def reset_notification_after_delay(order_id: int):
    await asyncio.sleep(60)
    async with async_session() as session:
        await session.execute(
            update(Order)
            .where(Order.id == order_id).values(notification=False)
            )
        await session.commit()




