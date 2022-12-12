from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

confirm_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="confirm"),
            KeyboardButton(text="/cancel"),
        ],
    ],
    resize_keyboard=True
)

lang_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Русский"),
            KeyboardButton(text="English"),
        ],
    ],
    resize_keyboard=True
)
