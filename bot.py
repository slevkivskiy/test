import asyncio
import logging
import os
import requests  # Щоб ходити в інтернет
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. Завантажуємо секрети
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_API_KEY")

# 2. Перевірка
if not TOKEN:
    exit("Error: BOT_TOKEN not found!")

# 3. Налаштування
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВІАТУРА (КНОПКИ) ---
kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌦 Погода Брусилів")],
        [KeyboardButton(text="💵 Курс Долара (Скоро)")]
    ],
    resize_keyboard=True
)

# --- ФУНКЦІЯ ПОГОДИ ---
def get_weather(city="Brusyliv"):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric&lang=ua"
        res = requests.get(url).json()
        
        temp = res["main"]["temp"]
        desc = res["weather"][0]["description"]
        wind = res["wind"]["speed"]
        
        return f"Погода в {city}:\n🌡 Температура: {temp}°C\n☁️ Небо: {desc}\n💨 Вітер: {wind} м/с"
    except Exception as e:
        return "⚠️ Не можу отримати погоду. Перевір API ключ."

# --- ОБРОБНИКИ (HANDLERS) ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привіт, Саня! Я тепер розумний бот. 🤖\nТисни кнопки знизу!", 
        reply_markup=kb
    )

@dp.message(F.text == "🌦 Погода Брусилів")
async def weather_handler(message: types.Message):
    await message.answer("Секунду, дивлюсь у вікно... 🔭")
    report = get_weather("Brusyliv")
    await message.answer(report)

@dp.message()
async def echo_handler(message: types.Message):
    await message.answer("Я поки розумію тільки кнопки! 👇", reply_markup=kb)

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())