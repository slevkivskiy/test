import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

# 1. Завантажуємо секрети
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# 2. Перевірка на дурня (чи є токен)
if not TOKEN:
    exit("Error: BOT_TOKEN not found! Check your .env file.")

# 3. Налаштування
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# 4. Реакція на /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Я живий! 🚀\nЯ працюю в Docker на AWS.")

# 5. Ехо (повторює текст)
@dp.message()
async def echo_handler(message: types.Message):
    await message.answer(f"Ти написав: {message.text}")

# 6. Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())