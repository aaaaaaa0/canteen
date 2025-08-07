import bot.keyboards as kb
import database.db_requests as rq
import logging
import httpx


from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.state import StateFilter, State, StatesGroup
from datetime import datetime
from sqlalchemy import select
from database.db_tabels import async_session, WorkTime


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


router = Router()


# ====================================================================
# COMMANDS
# ====================================================================


# Команда /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await rq.set_user(tg_id=message.from_user.id, chat_id=message.chat.id)
    await message.answer(
        "Здравствуйте! Здесь вы можете сделать заказ на доставку.",
        reply_markup=kb.make_order_kb
    )


# ====================================================================
# РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ
# ====================================================================


# Состояния для первичного сохранения контактной информации
class ContactInfo(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()


# Состояния для изменения контактной информации
class EditContactInfo(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()


# Форматирование Универсальная функция для отправки контактной информации
async def send_contact_info(user_id: int, message: Message | CallbackQuery):
    user = await rq.get_user_by_tg_id(user_id)
    contact_info = (
        "<b>Ваша контактная информация</b>\n\n"
        f"<b>ФИО:</b> {user.name}\n"
        f"<b>Номер телефона:</b> {user.phone}\n"
        f"<b>Адрес доставки заказа:</b> {user.address}"
    )
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(contact_info, reply_markup=kb.confirm_kb, parse_mode="HTML")
        await message.answer()
    else:
        await message.answer(contact_info, reply_markup=kb.confirm_kb, parse_mode="HTML")


# Кнопка [Сделать заказ]
@router.callback_query(F.data == "make_order")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ФИО:")
    await state.set_state(ContactInfo.waiting_for_name)
    await callback.answer()


# Ввод ФИО
@router.message(ContactInfo.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await rq.set_user_name(tg_id=message.from_user.id, name=message.text)
    await message.answer("Введите номер телефона:")
    await state.set_state(ContactInfo.waiting_for_phone)


# Ввод номера телефона
@router.message(ContactInfo.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    await rq.set_user_phone(tg_id=message.from_user.id, phone=message.text)
    await message.answer("Введите адрес доставки:")
    await state.set_state(ContactInfo.waiting_for_address)


# Ввод адреса и отправка всей контактной информации
@router.message(ContactInfo.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    await rq.set_user_address(tg_id=message.from_user.id, address=message.text)
    await send_contact_info(message.from_user.id, message)
    await state.clear()


# Кнопка [ПОДТВЕРДИТЬ]
@router.callback_query(F.data == "confirm_contact_info")
async def confirm_contact_info(callback: CallbackQuery):
    text = (
        "Данные сохранены.\n"
        "Вы можете в любое время просмотреть их и изменить.\n"
        "Для этого выберите в главном меню кнопку\n\n"
        "<b>[ Данные для заказа ]</b>"
    )
    await callback.message.answer(
        text,
        reply_markup=kb.main_keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# Кнопка [ИЗМЕНИТЬ]
@router.callback_query(F.data == "edit_contact_info")
async def edit_contact_info(callback: CallbackQuery):
    await callback.message.edit_text(
        "Что вы хотите изменить?",
        reply_markup=kb.edit_fields_kb
    )
    await callback.answer()


# Универсальная функция обновления данных
async def update_user_field(state: FSMContext, user_id: int, field: str, value: str, message: Message):
    if field == "name":
        await rq.set_user_name(user_id, value)
        await message.answer("ФИО успешно обновлено.")
    elif field == "phone":
        await rq.set_user_phone(user_id, value)
        await message.answer("Номер телефона успешно обновлён.")
    elif field == "address":
        await rq.set_user_address(user_id, value)
        await message.answer("Адрес доставки успешно обновлён.")
    await send_contact_info(user_id, message)
    await state.clear()


# Изменение ФИО
@router.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое ФИО:")
    await state.set_state(EditContactInfo.waiting_for_name)
    await callback.answer()


@router.message(EditContactInfo.waiting_for_name)
async def save_new_name(message: Message, state: FSMContext):
    await update_user_field(state, message.from_user.id, "name", message.text, message)


# Изменение номера телефона
@router.callback_query(F.data == "edit_phone")
async def edit_phone(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новый номер телефона:")
    await state.set_state(EditContactInfo.waiting_for_phone)
    await callback.answer()


@router.message(EditContactInfo.waiting_for_phone)
async def save_new_phone(message: Message, state: FSMContext):
    await update_user_field(state, message.from_user.id, "phone", message.text, message)


# Изменение адреса
@router.callback_query(F.data == "edit_address")
async def edit_address(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новый адрес доставки:")
    await state.set_state(EditContactInfo.waiting_for_address)
    await callback.answer()


@router.message(EditContactInfo.waiting_for_address)
async def save_new_address(message: Message, state: FSMContext):
    await update_user_field(state, message.from_user.id, "address", message.text, message)


@router.message(F.text == "Данные для заказа")
async def check_user_info(message: Message):
    await send_contact_info(message.from_user.id, message)


# ====================================================================
# ГЛАВНОЕ МЕНЮ
# ====================================================================

# Кнопка [Меню]
@router.message(F.text == "Меню")
async def catalog(message: Message):
    await message.answer("Выберите раздел меню:", reply_markup=await kb.menu_sections())


# Выбор раздела меню
@router.callback_query(F.data.startswith("menu_section_"))
async def collection(callback: CallbackQuery):
    await callback.answer("Вы выбрали раздел меню.")
    menu_section_id = int(callback.data.split("_")[2])
    keyboard = await kb.products(menu_section_id)
    await callback.message.answer(
        "Выберите блюдо из раздела:",  
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# Выбор блюда из раздела меню
@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    product_id = callback.data.split("_")[1]
    product_data = await rq.get_product_by_id(product_id)
    if product_data:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️",callback_data=f"menu_section_{product_data.menu_section_id}"),InlineKeyboardButton(text="Добавить в корзину",callback_data=f"add_to_cart_{product_id}")]])
        caption = (
            f"<b><i>{product_data.name}</i></b>\n"
            f"Цена: <b>{product_data.price} ₽</b>\n\n"
        )
        await callback.message.answer_photo(
            photo=product_data.image,  
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await callback.answer("Блюдо не найдено.", show_alert=True)


# Возврат в главное меню
@router.callback_query(F.data == "to_main_menu")
async def to_main_menu_handler(callback: CallbackQuery):
    await callback.message.answer("Вы в главном меню", reply_markup=kb.main_keyboard)
    await callback.answer()


# Возврат в раздел меню
@router.callback_query(F.data == "to_section_menu")
async def to_section_menu_handler(callback: CallbackQuery):
    await callback.message.answer("Выберите раздел меню:", reply_markup=await kb.menu_sections())
    await callback.answer()


# ====================================================================
# ДОБАВИТЬ В КОРЗИНУ
# ====================================================================


# Состояния для добавления товара в корзину
class AddToCartStates(StatesGroup):
    waiting_for_quantity = State()


# Обработчик кнопки "Добавить в корзину"
@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[3])
    await state.update_data(product_id=product_id)
    await callback.message.answer("Введите количество порций:")
    await state.set_state(AddToCartStates.waiting_for_quantity)
    await callback.answer()


# Функция для склонения слова "порция"
def get_portion_word(quantity: int) -> str:
    if quantity % 10 == 1 and quantity % 100 != 11:
        return "порция"
    elif 2 <= quantity % 10 <= 4 and not (12 <= quantity % 100 <= 14):
        return "порции"
    else:
        return "порций"


@router.callback_query(F.data.startswith("show_menu_sections_"))
async def collection(callback: CallbackQuery):
    menu_section_id = int(callback.data.split("_")[3])
    keyboard = await kb.products(menu_section_id)
    await callback.message.answer(
        "Выберите блюдо из раздела:",  
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )  


# Обработчик ввода количества порций и увеомление пользователя о добавлении товара в корзину
@router.message(StateFilter(AddToCartStates.waiting_for_quantity))
async def process_quantity(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Пожалуйста, введите число порций.")
        return
    quantity = int(message.text)
    if quantity <= 0:
        await message.answer("Количество порций должно быть больше 0.")
        return
    data = await state.get_data()
    product_id = data.get("product_id")
    product = await rq.get_product_by_id(product_id)
    if product is None:
        await message.answer("Товар не найден.")
        await state.clear()
        return
    await rq.add_to_cart(tg_id=message.from_user.id, product_id=product_id, quantity=quantity)
    portion_word = get_portion_word(quantity)
    total_price = int(product.price)* int(quantity)
    text = (
        f"<b>{product.name}</b>, {quantity} {portion_word}, {total_price} ₽\n"
        "✅ Добавлено в корзину."
    )
    menu_section_id = await rq.get_menu_section_id_by_product_id(product_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ К разделу меню",callback_data=f"show_menu_sections_{menu_section_id}")]])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.clear()

  
# ====================================================================
# КОРЗИНА
# ====================================================================


# Состояния для работы с корзиной
class CartStates(StatesGroup):
    waiting_for_delete_position = State()
    waiting_for_change_quantity = State()
    waiting_for_new_quantity = State()


# Форматирование корзины
def format_cart(cart_items):
    if not cart_items:
        return "🛒 Ваша корзина пуста."
    total_price = 0
    text = "<b>🛒 Ваша корзина:</b>\n\n"
    for idx, item in enumerate(cart_items, start=1):
        # item: (id, name, price, quantity)
        product_id, product_name, product_price, quantity = item
        item_total = int(product_price) * int(quantity)
        total_price += item_total
        text += (
            f"{idx}. <b>{product_name}</b>\n"
            f"Цена: {product_price}₽ | Кол-во: {quantity} | Сумма: {item_total}₽\n\n"
        )
    text += f"<b>Итого: {total_price}₽</b>"
    return text


# Обработчик кнопки "Корзина"
@router.message(F.text.lower() == "корзина")
async def show_cart(message: Message):
    user_id = message.from_user.id
    cart_items = await rq.get_cart(user_id)
    text = format_cart(cart_items)
    if text != "🛒 Ваша корзина пуста.":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Удалить позицию", callback_data="delete_position")],
            [InlineKeyboardButton(text="Изменить количество", callback_data="change_quantity")],
            [InlineKeyboardButton(text="Очистить корзину", callback_data="clear_cart")],
            [InlineKeyboardButton(text="ОФОРМИТЬ ЗАКАЗ", callback_data="checkout")]
        ])
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")


# Обработчик кнопки "Очистить корзину"
@router.callback_query(lambda c: c.data == "clear_cart")
async def clear_cart_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    user_id = await rq.get_internal_user_id(tg_id)  
    if not user_id:
        await callback.answer("Вы не зарегистрированы.")
        return
    await rq.clear_cart(user_id)  
    await callback.message.answer("🛒 Ваша корзина пуста.")
    await callback.answer("Корзина очищена ✅")


# Обработчик кнопки "Удалить позицию"
@router.callback_query(F.data.startswith("delete_position"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите номер позиции:",  parse_mode="HTML")
    await state.set_state(CartStates.waiting_for_delete_position)
    await callback.answer()


# Удалить позицию из корзины
@router.message(StateFilter(CartStates.waiting_for_delete_position))
async def process_delete_position(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Пожалуйста, введите номер позиции.")
        return
    position_number = int(message.text)
    if position_number <= 0:
        await message.answer("Номер позиции должен быть больше 0.")
        return
    user_id = message.from_user.id
    try:
        cart_items = await rq.get_cart(user_id)
    except ValueError:
        await message.answer("❌ Пользователь не найден. Возможно, вы не зарегистрированы.")
        await state.clear()
        return
    if position_number > len(cart_items):
        await message.answer("❌ Позиции с таким номером нет в корзине.")
        return
    product_id_to_remove = cart_items[position_number - 1][0]  
    await rq.remove_from_cart(user_id, product_id_to_remove)
    try:
        updated_cart_items = await rq.get_cart(user_id)
    except ValueError:
        await message.answer("❌ Пользователь не найден. Возможно, вы не зарегистрированы.")
        await state.clear()
        return
    if not updated_cart_items:
        await message.answer("🛒 Ваша корзина теперь пуста.")
        await state.clear()
        return
    text = format_cart(updated_cart_items)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить позицию", callback_data="delete_position")],
        [InlineKeyboardButton(text="Изменить количество", callback_data="change_quantity")],
        [InlineKeyboardButton(text="Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton(text="ОФОРМИТЬ ЗАКАЗ", callback_data="checkout")]
    ])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer("✅ Позиция удалена из корзины.")
    await state.clear()


# Обработка кнопки "Изменить количество"
@router.callback_query(F.data == "change_quantity")
async def change_quantity_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите номер позиции в корзине, которую хотите изменить:")
    await state.set_state(CartStates.waiting_for_change_quantity)


# Пользователь отправил номер позиции
@router.message(StateFilter(CartStates.waiting_for_change_quantity))
async def process_position_number(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Пожалуйста, введите номер позиции числом.")
        return
    position_number = int(message.text)
    cart_items = await rq.get_cart(message.from_user.id)
    if position_number < 1 or position_number > len(cart_items):
        await message.answer("Такой позиции нет в корзине. Проверьте номер и попробуйте снова.")
        return
    product_id = cart_items[position_number - 1][0]
    await state.update_data(product_id=product_id)
    await message.answer("Введите новое количество для этой позиции:")
    await state.set_state(CartStates.waiting_for_new_quantity)


# Пользователь отправил новое количество
@router.message(StateFilter(CartStates.waiting_for_new_quantity))
async def process_new_quantity(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Пожалуйста, введите количество числом.")
        return
    new_quantity = int(message.text)
    if new_quantity <= 0:
        await message.answer("Количество должно быть больше 0.")
        return
    data = await state.get_data()
    product_id = data.get("product_id")
    await rq.update_cart_quantity(user_id=message.from_user.id, product_id=product_id, quantity=new_quantity)
    tg_id = message.from_user.id  
    try:
        cart_items = await rq.get_cart(tg_id)
    except ValueError:
        await message.answer("❌ Пользователь не найден. Возможно, вы не зарегистрированы.")
        await state.clear()
        return
    if not cart_items:
        await message.answer("🛒 Ваша корзина пуста.")
        await state.clear()
        return
    text = format_cart(cart_items)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить позицию", callback_data="delete_position")],
        [InlineKeyboardButton(text="Изменить количество", callback_data="change_quantity")],
        [InlineKeyboardButton(text="Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton(text="ОФОРМИТЬ ЗАКАЗ", callback_data="checkout")]
    ])
    await message.answer("✅ Количество обновлено.")
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.clear()


# ===================================================================
# ОПЛАТА И ПОДТВЕРЖДЕНИЕ ЗАКАЗА
# ====================================================================


# Кнопка [ОФОРМИТЬ ЗАКАЗ]
@router.callback_query(F.data == "checkout")
async def start_registration(callback: CallbackQuery):
    text = (
        "<b>Важно!</b> \n\n"
        "⁘ Перед оформлением, пожалуйста, проверьте данные  для заказа.\n\n"
        "⁘ Также убедитесь, что все товары и их количество в корзине выбраны правильно.\n\n"
        "⁘ После подтверждения заказа вам будет выслана ссылка для оплаты.\n\n"
        "⁘ При возникновении проблем, свяжитесь с администратором: +79990007788"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Подтвердить заказ", callback_data="confirm_order")]])
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# Отправка уведомления о новых заказах администраторам
async def send_order_to_admin(order_id: int):
    try:
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:8000/notify", json={"order_id": order_id})
    except Exception as e:
        print(f"❌ Ошибка при отправке уведомления админу: {e}")


# Кнопка [Подтвердить заказ]
@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    now = datetime.now().time()
    async with async_session() as session:
        result = await session.execute(
            select(WorkTime)
            .where(WorkTime.id == 1)
            )
        time_data = result.scalar_one()
        if not time_data.stop:
            await callback.message.answer("🚫 Приём заказов временно остановлен.")
            await callback.answer()
            return
        if not (time_data.start <= now <= time_data.end):
            await callback.message.answer(
                f"🚫 Сейчас нельзя сделать заказ. Заказы принимаются с "
                f"{time_data.start.strftime('%H:%M')} до {time_data.end.strftime('%H:%M')}."
            )
            await callback.answer()
            return
    cart_items = await rq.get_cart(tg_id)
    if not cart_items:
        await callback.message.answer("🛒 Ваша корзина пуста.")
        await callback.answer()
        return
    order_id = await rq.confirm_order(tg_id)
    await send_order_to_admin(order_id)
    await callback.message.answer(
        f"✅ Заказ №{order_id} принят! Мы свяжемся с вами в ближайшее время.",
        reply_markup=kb.main_keyboard
    )
    await callback.answer()
