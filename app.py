from aiogram import executor
from preload.load_all import bot


async def on_shutdown():
    await bot.close()


if __name__ == '__main__':
    from users.user_panel import dp
    executor.start_polling(dp, on_shutdown=on_shutdown)