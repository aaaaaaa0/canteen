from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


main_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Добавить ссылку на оплату')], [KeyboardButton(text='Время приёма заказов')]],resize_keyboard=True)