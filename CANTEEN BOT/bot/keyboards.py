from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db_requests import get_menu_sections, get_products_by_menu_section

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# Клавиатура для главного меню
main_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Меню')], [KeyboardButton(text='Корзина')],[KeyboardButton(text='Данные для заказа')],],resize_keyboard=True)


# Клавиатура для кнопки [СДЕЛАТЬ ЗАКАЗ]
make_order_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Сделать заказ", callback_data="make_order")]])


# Клавиатура отправляется вместе с полной контактной информацией пользователя
confirm_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 ИЗМЕНИТЬ", callback_data="edit_contact_info"),
            InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ", callback_data="confirm_contact_info"),
        ]
    ]
)


reconfirm_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 ИЗМЕНИТЬ", callback_data="edit_contact_info"),
            InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ", callback_data="confirm_order"),
        ]
    ]
)



# Клавиатура отправляется после нажатия на кнопку [ИЗМЕНИТЬ] в сообщении с контактной информацией
# Позволяет пользователю изменить контактные данные
edit_fields_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Изменить ФИО", callback_data="edit_name")],
        [InlineKeyboardButton(text="Изменить номер телефона", callback_data="edit_phone")],
        [InlineKeyboardButton(text="Изменнить адрес доставки", callback_data="edit_address")],
    ]
)


# Клавиатура для выбора раздела меню
async def menu_sections(menu_section_id=None):
    all_menu_sections = await get_menu_sections()  
    keyboard = InlineKeyboardBuilder()
    
    for menu_section in all_menu_sections:
        cb_data = f"menu_section_{menu_section.id}"
        keyboard.add(
            InlineKeyboardButton(
                text=menu_section.name,
                callback_data=cb_data
            )
        )
    
    return keyboard.adjust(2).as_markup()


# Клавиатура для выбора блюда в категории меню
async def products(menu_section_id):
    all_products = await get_products_by_menu_section(menu_section_id)
    keyboard = InlineKeyboardBuilder()

    for product in all_products:
        cb_data = f"product_{product.id}"
        keyboard.add(
            InlineKeyboardButton(
                text=product.name,
                callback_data=cb_data
            )
        )
    keyboard.add(
        InlineKeyboardButton(
            text='⬅️',
            callback_data='to_section_menu'
        )
    )
    
    return keyboard.adjust(1).as_markup()

