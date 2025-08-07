import logging


from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# Главное меню
main_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Добавить ссылку для оплаты заказа')], 
                                              [KeyboardButton(text='Удалить ссылку для оплаты заказа')],
                                              [KeyboardButton(text='Уведомить о новой ссылке для оплаты')], 
                                              [KeyboardButton(text='Время приёма заказов')]], 
                                              resize_keyboard=True)


# Кнопка отправляеется с сообщением о заказе после нажатия на кнопку в главном меню [Добавить ссылку для оплаты заказа]
add_check_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ДОБАВИТЬ ССЫЛКУ", callback_data="confirm_order_check")]])


# Кнопка отправляеется с сообщением о заказе после нажатия на кнопку в главном меню [Удалить ссылку для оплаты заказа]
del_check_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="УДАЛИТЬ ССЫЛКУ", callback_data="confirm_delete_check")]])


# Регулирование времени приёма заказов в польщовательском боте. Отправляется после нажатия на кнопку в главном меню [Время приёма заказов]
def work_time_keyboard():
    buttons = [
        [InlineKeyboardButton(text="ИЗМЕНИТЬ НАЧАЛО", callback_data="change_start")],
        [InlineKeyboardButton(text="ИЗМЕНИТЬ ОКОНЧАНИЕ", callback_data="change_end")],
        [InlineKeyboardButton(text="ВКЛ\\ВЫКЛ ПРИЁМ ЗАКАЗОВ", callback_data="toggle_stop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Кнопка отправляеется с сообщением о заказе после нажатия на кнопку в главном меню [Уведомить о новой ссылке для оплаты]
notify_check_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ОТПРАВИТЬ ССЫЛКУ", callback_data="confirm_notify")]])



