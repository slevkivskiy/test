import asyncio
import logging
import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. Завантаження
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# 2. Налаштування AI з АВТОПОШУКОМ МОДЕЛІ
model = None
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        
        # --- ДІАГНОСТИКА: Дивимось, що доступно ---
        print("🔍 ШУКАЮ ДОСТУПНІ МОДЕЛІ...")
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"📋 СПИСОК МОДЕЛЕЙ: {available_models}")

        if available_models:
            # Беремо першу-ліпшу (зазвичай це gemini-pro або gemini-1.5-flash)
            selected_model = available_models[0]
            # Якщо є flash - беремо її пріоритетно
            for m in available_models:
                if 'flash' in m:
                    selected_model = m
                    break
            
            print(f"✅ ОБРАНО МОДЕЛЬ: {selected_model}")
            model = genai.GenerativeModel(selected_model)
        else:
            print("❌ НЕМАЄ ДОСТУПНИХ МОДЕЛЕЙ ДЛЯ ЦЬОГО КЛЮЧА!")
            
    except Exception as e:
        print(f"❌ ПОМИЛКА ПІДКЛЮЧЕННЯ AI: {e}")

# 3. Бот
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌦 Погода Брусилів")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Я живий! 🤖\nПиши мені, я спробую відповісти.", reply_markup=kb)

@dp.message(F.text == "🌦 Погода Брусилів")
async def weather_handler(message: types.Message):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Brusyliv&appid={WEATHER_KEY}&units=metric&lang=ua"
        data = requests.get(url).json()
        temp = data["main"]["temp"]
        await message.answer(f"Температура: {temp}°C")
    except:
        await message.answer("Помилка погоди.")

@dp.message()
async def ai_chat(message: types.Message):
    if not model:
        await message.answer("⚠️ Мої мізки не працюють. Адмін, дивись логи!")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        response = model.generate_content(message.text)
        await message.answer(response.text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Помилка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())