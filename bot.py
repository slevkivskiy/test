import asyncio
import logging
import os
import time  # <--- Для заміру часу
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from prometheus_client import start_http_server, Counter, Summary  # <--- Нові інструменти

# --- 1. CONFIG & METRICS DEFINITION ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# 🔥 МЕТРИКИ (HARDCORE LEVEL)
# 1. Загальний лічильник команд (розбиваємо по типах: погода, ai, старт)
COMMAND_COUNTER = Counter('bot_commands_total', 'Total number of commands', ['command_type'])

# 2. Лічильник помилок (щоб знати, коли все горить)
ERROR_COUNTER = Counter('bot_errors_total', 'Total number of errors', ['error_type'])

# 3. Таймер: скільки часу ШІ генерує відповідь (Latency)
AI_LATENCY = Summary('bot_ai_latency_seconds', 'Time spent processing AI request')

# 4. Таймер: скільки часу займає запит погоди
WEATHER_LATENCY = Summary('bot_weather_latency_seconds', 'Time spent fetching weather')

# --- 2. SETUP AI ---
model = None
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logging.error(f"AI Setup Error: {e}")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌦 Погода Брусилів")]],
    resize_keyboard=True
)

# --- 3. HANDLERS WITH METRICS ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Рахуємо команду
    COMMAND_COUNTER.labels(command_type='start').inc()
    
    await message.answer("Моніторинг активовано. Системи в нормі. 🟢", reply_markup=kb)

@dp.message(F.text == "🌦 Погода Брусилів")
async def weather_handler(message: types.Message):
    # Рахуємо запит
    COMMAND_COUNTER.labels(command_type='weather').inc()
    
    start_time = time.time() # ⏱ Засікаємо час
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Brusyliv&appid={WEATHER_KEY}&units=metric&lang=ua"
        data = requests.get(url).json()
        
        # Фіксуємо час виконання
        duration = time.time() - start_time
        WEATHER_LATENCY.observe(duration)
        
        temp = data["main"]["temp"]
        await message.answer(f"🌡 {temp}°C (Запит зайняв: {duration:.2f}с)")
    except Exception as e:
        ERROR_COUNTER.labels(error_type='weather_api').inc()
        await message.answer("⚠️ Помилка погоди.")

@dp.message()
async def ai_chat(message: types.Message):
    # Рахуємо повідомлення до AI
    COMMAND_COUNTER.labels(command_type='ai_chat').inc()
    
    if not model:
        await message.answer("⚠️ AI вимкнено.")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    start_time = time.time() # ⏱ Засікаємо, скільки думає Gemini
    try:
        response = model.generate_content(message.text)
        
        duration = time.time() - start_time
        AI_LATENCY.observe(duration) # Записуємо в метрики
        
        await message.answer(response.text, parse_mode="Markdown")
    except Exception as e:
        ERROR_COUNTER.labels(error_type='ai_generation').inc()
        await message.answer(f"Помилка AI: {e}")

async def main():
    # Запускаємо сервер метрик на 8000 порту
    start_http_server(8000)
    logging.info("🔥 PRO Metrics server running on port 8000")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())