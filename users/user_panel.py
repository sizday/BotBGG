from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.dispatcher.filters import Command, CommandStart
from others.sticker_id import positive_sticker, negative_sticker
from preload.load_all import dp
from state.state import Dialog
from others.function import get_rating_from_bgg, get_overall_df, create_predict, create_str_from_dict
import random


@dp.message_handler(CommandStart())
async def predict_user(message: Message):
    await message.answer('Чтобы получить информацию о твоих оценках, введи свой логин с сайте bgg')
    await Dialog.waiting_username.set()


@dp.message_handler(state=Dialog.waiting_username)
async def wait_username(message: Message, state: FSMContext):
    username = message.text.lower()
    user_bgg_dict = get_rating_from_bgg(username)
    count_ratings = len(user_bgg_dict)
    if count_ratings > 0:
        await message.answer(f"Спасибо за предоставленные данные. В твоем аккаунте {count_ratings} оценок. "
                             f"Далее необходимо немного подождать для получений предсказания")
        await message.answer_sticker(positive_sticker.get(random.randint(0, len(positive_sticker))))
        data = get_overall_df(username, user_bgg_dict)
        result_dict = create_predict(data, username)
        result_str = create_str_from_dict(result_dict)
        await message.answer(f"Ваши итоговые игры:\n{result_str}")
    else:
        await message.answer("К сожалению, в твоем аккаунте нет оценок и мы не можем сделать предсказание.")
        await message.answer_sticker(negative_sticker.get(random.randint(0, len(negative_sticker))))
        await state.reset_state()


@dp.message_handler(state=Dialog.predict_games)
async def predict(message: Message, state: FSMContext):
    pass
