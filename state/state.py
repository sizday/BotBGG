from aiogram.dispatcher.filters.state import StatesGroup, State


class Prediction(StatesGroup):
    waiting_username = State()
    waiting_size = State()
    predict_games = State()


class Similar(StatesGroup):
    waiting_size = State()
    waiting_game = State()
    predict_games = State()
