import asyncio
import logging
import os
import time  # <--- Додав для вимірювання часу
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
# --- МЕТРИКИ ---
from prometheus_client import start_http_server, Counter, Summary

# 1. Завантаження
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# --- ВИЗНАЧЕННЯ МЕТРИК ---
# Лічильник усіх команд (розбиваємо по типах: start, weather, ai)
COMMAND_COUNTER = Counter('bot_commands_total', 'Total commands', ['command_type'])
# Лічильник помилок
ERROR_COUNTER = Counter('bot_errors_total', 'Total errors', ['error_type'])
# Час відповіді AI
AI_LATENCY = Summary('bot_ai_latency_seconds', 'Time spent processing AI request')
# Час відповіді Погоди
WEATHER_LATENCY = Summary('bot_weather_latency_seconds', 'Time spent fetching weather')


# 2. Налаштування AI з АВТОПОШУКОМ МОДЕЛІ (Твій робочий код)
model = None
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        
        # --- ДІАГНОСТИКА ---
        print("🔍 ШУКАЮ ДОСТУПНІ МОДЕЛІ...")
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"📋 СПИСОК МОДЕЛЕЙ: {available_models}")

        if available_models:
            selected_model = available_models[0]
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
    # Метрика: хтось натиснув старт
    COMMAND_COUNTER.labels(command_type='start').inc()
    await message.answer("Я живий! 🤖\nПиши мені, я спробую відповісти.", reply_markup=kb)

@dp.message(F.text == "🌦 Погода Брусилів")
async def weather_handler(message: types.Message):
    # Метрика: запит погоди
    COMMAND_COUNTER.labels(command_type='weather').inc()
    
    start_time = time.time() # ⏱ Засікаємо час
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Brusyliv&appid={WEATHER_KEY}&units=metric&lang=ua"
        data = requests.get(url).json()
        
        # Метрика: скільки часу це зайняло
        duration = time.time() - start_time
        WEATHER_LATENCY.observe(duration)

        temp = data["main"]["temp"]
        await message.answer(f"Температура: {temp}°C")
    except Exception as e:
        # Метрика: помилка
        ERROR_COUNTER.labels(error_type='weather').inc()
        await message.answer("Помилка погоди.")

@dp.message()
async def ai_chat(message: types.Message):
    # Метрика: пишуть в AI
    COMMAND_COUNTER.labels(command_type='ai_chat').inc()

    if not model:
        await message.answer("⚠️ Мої мізки не працюють. Адмін, дивись логи!")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    start_time = time.time() # ⏱ Засікаємо час
    try:
        response = model.generate_content(message.text)
        
        # Метрика: скільки думав AI
        duration = time.time() - start_time
        AI_LATENCY.observe(duration)

        await message.answer(response.text, parse_mode="Markdown")
    except Exception as e:
        # Метрика: помилка AI
        ERROR_COUNTER.labels(error_type='ai_error').inc()
        await message.answer(f"Помилка: {e}")

async def main():
    # 🔥 ЗАПУСК СЕРВЕРА МЕТРИК (Порт 8000)
    start_http_server(8000)
    print("📈 Metrics server running on port 8000")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())