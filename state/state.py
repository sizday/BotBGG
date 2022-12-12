from aiogram.dispatcher.filters.state import StatesGroup, State


class Dialog(StatesGroup):
    waiting_username = State()
    predict_games = State()
