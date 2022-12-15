from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.dispatcher.filters import Command, CommandStart
from others.sticker_id import positive_sticker, negative_sticker
from preload.load_all import dp
from state.state import Dialog
from others.function import get_rating_from_bgg_csv, get_overall_df, create_predict, \
    create_str_from_dict, get_rating_from_bgg_xml
import random


@dp.message_handler(CommandStart())
async def predict_user(message: Message):
    await message.answer('Чтобы сделать предсказание, мне необходим твой логин с сайта BoardGamesGeek.com')
    await Dialog.waiting_username.set()


@dp.message_handler(state=Dialog.waiting_username)
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
            await Dialog.predict_games.set()
        else:
            await message.answer("К сожалению, в твоем аккаунте нет оценок и мы не можем сделать предсказание.")
            await message.answer_sticker(negative_sticker.get(random.randint(0, len(negative_sticker)-1)))
            await state.reset_state()


@dp.message_handler(state=Dialog.predict_games)
async def predict(message: Message, state: FSMContext):
    count = message.text.lower()
    state_data = await state.get_data()
    data = state_data.get("user_data")
    username = state_data.get("username")
    await message.answer(f"Дальнейший процесс займет некоторое время (около 30 секунд). Никуда не уходи!)")
    result_dict = create_predict(data, username, count)
    result_str = create_str_from_dict(result_dict)
    await message.answer(f"Ваши итоговые игры:\n{result_str}")
    await state.reset_state()


@dp.message_handler(Command("cancel"), state=Dialog.predict_games)
async def cancel(message: Message, state: FSMContext):
    await message.answer("Вы отменили предсказание игр")
    await state.reset_state()
