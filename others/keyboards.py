from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

data_size_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Быстрее"),
            KeyboardButton(text="Точнее"),
        ],
    ],
    resize_keyboard=True
)
