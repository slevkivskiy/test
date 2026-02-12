import asyncio
import logging
import os
import time
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
# Спроба імпорту метрик
try:
    from prometheus_client import start_http_server, Counter, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# --- 1. КОНФІГ ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# --- 2. МЕТРИКИ ---
if PROMETHEUS_AVAILABLE:
    # Лічильники
    COMMAND_COUNTER = Counter('bot_commands_total', 'Total commands', ['command_type'])
    ERROR_COUNTER = Counter('bot_errors_total', 'Total errors', ['error_type'])
    # Таймери
    AI_LATENCY = Summary('bot_ai_latency_seconds', 'AI processing time')
    WEATHER_LATENCY = Summary('bot_weather_latency_seconds', 'Weather fetch time')

# --- 3. НАЛАШТУВАННЯ AI (FIXED) ---
model = None
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        # ⚠️ ЖОРСТКО СТАВИМО 1.5-FLASH (Вона стабільна і має великі ліміти)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ AI підключено: gemini-1.5-flash")
    except Exception as e:
        print(f"⚠️ AI Init Error: {e}")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌦 Погода Брусилів")]],
    resize_keyboard=True
)

# --- 4. ОБРОБНИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if PROMETHEUS_AVAILABLE:
        COMMAND_COUNTER.labels(command_type='start').inc()
    await message.answer("Ліміти пофікшено. Працюємо далі! 🚀", reply_markup=kb)

@dp.message(F.text == "🌦 Погода Брусилів")
async def weather_handler(message: types.Message):
    if PROMETHEUS_AVAILABLE:
        COMMAND_COUNTER.labels(command_type='weather').inc()
    
    start_time = time.time()
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Brusyliv&appid={WEATHER_KEY}&units=metric&lang=ua"
        data = requests.get(url).json()
        
        if PROMETHEUS_AVAILABLE:
            WEATHER_LATENCY.observe(time.time() - start_time)
        
        temp = data["main"]["temp"]
        await message.answer(f"🌡 Температура: {temp}°C")
    except Exception as e:
        if PROMETHEUS_AVAILABLE:
            ERROR_COUNTER.labels(error_type='weather_api').inc()
        await message.answer(f"⚠️ Помилка погоди: {e}")

@dp.message()
async def ai_chat(message: types.Message):
    if PROMETHEUS_AVAILABLE:
        COMMAND_COUNTER.labels(command_type='ai_chat').inc()

    if not model:
        await message.answer("❌ AI вимкнено.")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    start_time = time.time()
    try:
        response = model.generate_content(message.text)
        
        if PROMETHEUS_AVAILABLE:
            AI_LATENCY.observe(time.time() - start_time)
        
        await message.answer(response.text)
        
    except Exception as e:
        if PROMETHEUS_AVAILABLE:
            ERROR_COUNTER.labels(error_type='ai_limit').inc()
        # Якщо знову 429 - пишемо зрозуміло
        if "429" in str(e):
            await message.answer("⏳ Ой, я перегрівся (Ліміт запитів). Почекай 10 секунд.")
        else:
            await message.answer(f"Error: {e}")

async def main():
    if PROMETHEUS_AVAILABLE:
        start_http_server(8000)
        logging.info("🔥 Metrics server running on port 8000")
        
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())