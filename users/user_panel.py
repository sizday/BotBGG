from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.dispatcher.filters import Command, CommandStart
from others.sticker_id import positive_sticker, negative_sticker
from preload.load_all import dp
from state.state import Prediction, Similar
from others.function import get_rating_from_bgg_csv, get_overall_df, predict, \
    create_str_from_dict, get_rating_from_bgg_xml, load_data_from_file, get_game_id_by_name, Method
import random


@dp.message_handler(CommandStart())
async def predict_user(message: Message):
    await message.answer('Чтобы сделать предсказание, мне необходим твой логин с сайта boardgamesgeek.com')
    await Prediction.waiting_username.set()


@dp.message_handler(state=Prediction.waiting_username)
async def wait_username(message: Message, state: FSMContext):
    username = message.text.lower()
    user_df = get_rating_from_bgg_csv(username)
    if user_df is None:
        user_df = get_rating_from_bgg_xml(username)
    if user_df is None:
        await message.answer("К сожалению, возникла ошибка, и мне не удалось выгрузить игры из твоего аккаунта.")
        await message.answer_sticker(negative_sticker.get(random.randint(0, len(negative_sticker)-1)))
        await state.reset_state()
    else:
        count_ratings = user_df.shape[0]
        if count_ratings > 0:
            await message.answer(f"Спасибо за предоставленные данные. В твоем аккаунте {count_ratings} оценок.")
            await message.answer_sticker(positive_sticker.get(random.randint(0, len(positive_sticker)-1)))
            await message.answer(f"Напиши сколько игр ты хочешь получить?")
            data = get_overall_df(user_df)
            await state.update_data(user_data=data)
            await state.update_data(username=username)
            await Prediction.predict_games.set()
        else:
            await message.answer("К сожалению, в твоем аккаунте нет оценок и мы не можем сделать предсказание.")
            await message.answer_sticker(negative_sticker.get(random.randint(0, len(negative_sticker)-1)))
            await state.reset_state()


@dp.message_handler(state=Prediction.predict_games)
async def predict_games(message: Message, state: FSMContext):
    count = message.text.lower()
    state_data = await state.get_data()
    data = state_data.get("user_data")
    username = state_data.get("username")
    await message.answer(f"Дальнейший процесс займет некоторое время (около 30 секунд). Никуда не уходи!)")
    result_dict = predict(data, username, count, Method.recommend)
    result_str = create_str_from_dict(result_dict)
    await message.answer(f"Ваши итоговые игры:\n{result_str}")
    await state.reset_state()


@dp.message_handler(Command("similar"))
async def cancel(message: Message):
    await message.answer('Напиши название игры, для которой ты хочешь найти схожие!')
    await Similar.waiting_game.set()


@dp.message_handler(state=Similar.waiting_game)
async def wait_game(message: Message, state: FSMContext):
    game_name = message.text.lower()
    data = load_data_from_file()
    game_id = get_game_id_by_name(data, game_name)
    if game_id is None:
        await message.answer("К сожалению, я не смог найти такую игру. Попробуйте другую")
        await message.answer_sticker(negative_sticker.get(random.randint(0, len(negative_sticker) - 1)))
        await state.reset_state()
    else:
        await message.answer_sticker(positive_sticker.get(random.randint(0, len(positive_sticker) - 1)))
        await message.answer(f"Я нашел такую игру. Напиши сколько похожих игр ты хочешь получить?")
        await state.update_data(game_id=game_id)
        await state.update_data(data=data)
        await Similar.predict_games.set()


@dp.message_handler(state=Similar.predict_games)
async def predict_similar(message: Message, state: FSMContext):
    count = message.text.lower()
    state_data = await state.get_data()
    data = state_data.get("game_id")
    username = state_data.get("data")
    result_dict = predict(data, username, count, Method.similar)
    result_str = create_str_from_dict(result_dict)
    await message.answer(f"На заданную игру я нашел похожими вот такие игры:\n{result_str}")
    await state.reset_state()


@dp.message_handler(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await message.answer("Вы отменили работу робота")
    await state.reset_state()
