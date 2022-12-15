from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.dispatcher.filters import Command, CommandStart
from others.sticker_id import positive_sticker, negative_sticker
from preload.load_all import dp
from others.keyboards import data_size_menu
from aiogram.utils.markdown import hlink
from state.state import Prediction, Similar
from others.function import get_rating_from_bgg_csv, get_overall_df, predict, \
    create_str_from_dict, get_rating_from_bgg_xml, load_data_from_file, get_game_id_by_name, Method, DataSize
import random


@dp.message_handler(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await message.answer("Вы отменили заданное боту задание")
    await state.reset_state()


@dp.message_handler(CommandStart())
async def predict_user(message: Message):
    await message.answer('В данном боте есть 2 функции:\n'
                         '1. Предсказание новых настольных игр на основе данных с BGG - /predict\n'
                         '2. Поиск похожих игр на определенную игру - /similar')


@dp.message_handler(Command("predict"))
async def predict_user(message: Message):
    bgg_link = hlink('BoardGamesGeek', 'https://boardgamegeek.com/')
    await message.answer(f'Чтобы сделать предсказание, мне необходим твой логин с сайта {bgg_link}')
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
            await message.answer(f"Выбери режим предсказания:\n"
                                 f"1. Быстрее, но не идеально точно, так как обучение идет на небольшом объеме данных\n"
                                 f"2. Точнее, но, к сожалению, медленнее",
                                 reply_markup=data_size_menu)
            await state.update_data(username=username)
            await state.update_data(user_df=user_df)
            await Prediction.waiting_size.set()
        else:
            await message.answer("К сожалению, в твоем аккаунте нет оценок и мы не можем сделать предсказание.")
            await message.answer_sticker(negative_sticker.get(random.randint(0, len(negative_sticker)-1)))
            await state.reset_state()


@dp.message_handler(state=Prediction.waiting_size)
async def get_predict_size(message: Message, state: FSMContext):
    data_size = message.text.lower()
    time = ''
    if data_size == 'быстрее':
        data_size = DataSize.small
        time = '15-30 секунд'
    elif data_size == 'точнее':
        data_size = DataSize.large
        time = '2-3 минуты'
    else:
        await message.answer(f"Такой вариант не предусмотрен. Выбери из двух заданных.")
        await Prediction.waiting_size.set()
    state_data = await state.get_data()
    user_df = state_data.get("user_df")
    data = get_overall_df(user_df, data_size)
    await message.answer(f"Напиши сколько игр ты хочешь получить?")
    await state.update_data(user_data=data)
    await state.update_data(predict_time=time)
    await Prediction.predict_games.set()


@dp.message_handler(state=Prediction.predict_games)
async def predict_games(message: Message, state: FSMContext):
    count = message.text.lower()
    state_data = await state.get_data()
    data = state_data.get("user_data")
    username = state_data.get("username")
    predict_time = state_data.get("predict_time")
    if count.isdigit():
        count = int(count)
        if count > 0:
            await message.answer(f"Дальнейший процесс займет некоторое время ({predict_time}). Никуда не уходи!")
            result_dict = predict(data, username, count, Method.recommend)
            result_str = create_str_from_dict(result_dict)
            await message.answer(f"Ваши итоговые игры:\n{result_str}")
            await state.reset_state()
        else:
            await message.answer(f"Введеное значение должно быть больше нуля. Введите значение заново.")
            await Prediction.predict_games.set()
    else:
        await message.answer(f"Введеное значение не является числом. Введите значение заново.")
        await Prediction.predict_games.set()


@dp.message_handler(Command("similar"))
async def cancel(message: Message):
    await message.answer(f"Для начала выбери режим поиска игр:\n"
                         f"1. Быстрее, но не идеально точно, так как обучение идет на небольшом объеме данных\n"
                         f"2. Точнее, но, к сожалению, медленнее", reply_markup=data_size_menu)
    await Similar.waiting_size.set()


@dp.message_handler(state=Similar.waiting_size)
async def get_similar_size(message: Message, state: FSMContext):
    data_size = message.text.lower()
    time = ''
    if data_size == 'быстрее':
        data_size = DataSize.small
        time = '15-30 секунд'
    elif data_size == 'точнее':
        data_size = DataSize.large
        time = '2-3 минуты'
    else:
        await message.answer(f"Такой вариант не предусмотрен. Выбери из двух заданных.")
        await Similar.waiting_size.set()
    await message.answer('Теперь напиши название игры, для которой ты хочешь найти схожие! '
                         'Главное - необходимо писать точное название на английском языке')
    data = load_data_from_file(data_size)
    await state.update_data(bgg_data=data)
    await state.update_data(predict_time=time)
    await Similar.waiting_game.set()


@dp.message_handler(state=Similar.waiting_game)
async def wait_game(message: Message, state: FSMContext):
    game_name = message.text.lower().title()
    state_data = await state.get_data()
    data = state_data.get("bgg_data")
    game_id = get_game_id_by_name(data, game_name)
    if game_id is None:
        await message.answer("К сожалению, я не смог найти такую игру. Попробуйте другую")
        await message.answer_sticker(negative_sticker.get(random.randint(0, len(negative_sticker) - 1)))
        await state.reset_state()
    else:
        await message.answer_sticker(positive_sticker.get(random.randint(0, len(positive_sticker) - 1)))
        await message.answer(f"Я нашел такую игру. Напиши сколько похожих игр ты хочешь получить?")
        await state.update_data(game_id=game_id)
        await Similar.predict_games.set()


@dp.message_handler(state=Similar.predict_games)
async def predict_similar(message: Message, state: FSMContext):
    count = message.text.lower()
    state_data = await state.get_data()
    data = state_data.get("bgg_data")
    game_id = state_data.get("game_id")
    predict_time = state_data.get("predict_time")
    if count.isdigit():
        count = int(count)
        if count > 0:
            await message.answer(f"Дальнейший процесс займет некоторое время ({predict_time}). Никуда не уходи!")
            result_dict = predict(data, game_id, count, Method.similar)
            result_str = create_str_from_dict(result_dict)
            await message.answer(f"На заданную игру я нашел похожими вот такие игры:\n{result_str}")
            await state.reset_state()
        else:
            await message.answer(f"Введеное значение должно быть больше нуля. Введите значение заново.")
            await Similar.predict_games.set()
    else:
        await message.answer(f"Введеное значение не является числом. Введите значение заново.")
        await Similar.predict_games.set()
