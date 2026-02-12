import asyncio
import logging
import os
import time
import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- 1. БЕЗПЕЧНІ ІМПОРТИ ---
try:
    from groq import Groq
    GROQ_LIB_OK = True
except ImportError:
    GROQ_LIB_OK = False
    print("⚠️ Бібліотека 'groq' не встановлена!")

try:
    from prometheus_client import start_http_server, Counter, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# --- 2. КОНФІГ ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_API_KEY")
AI_KEY = os.getenv("AI_KEY")

# --- 3. МЕТРИКИ ---
if PROMETHEUS_AVAILABLE:
    COMMAND_COUNTER = Counter('bot_commands_total', 'Total commands', ['command_type'])
    ERROR_COUNTER = Counter('bot_errors_total', 'Total errors', ['error_type'])
    AI_LATENCY = Summary('bot_ai_latency_seconds', 'AI processing time')

# --- 4. НАЛАШТУВАННЯ AI ---
client = None
AI_STATUS = "Вимкнено"

if GROQ_LIB_OK and AI_KEY:
    try:
        client = Groq(api_key=AI_KEY)
        AI_STATUS = "✅ Groq (Llama 3)"
    except Exception as e:
        AI_STATUS = f"❌ Помилка ключа: {e}"
else:
    if not GROQ_LIB_OK: AI_STATUS = "❌ Немає бібліотеки 'groq'"
    if not AI_KEY: AI_STATUS = "❌ Немає AI_KEY в .env"

# --- 5. БОТ ---
logging.basicConfig(level=logging.INFO)
try:
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
except Exception as e:
    print(f"💀 КРИТИЧНА ПОМИЛКА: Невірний BOT_TOKEN. {e}")
    exit(1)

kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌦 Погода Брусилів")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if PROMETHEUS_AVAILABLE:
        COMMAND_COUNTER.labels(command_type='start').inc()
    await message.answer(f"Я піднявся! 🧟‍♂️\nСтатус AI: {AI_STATUS}", reply_markup=kb)

@dp.message(F.text == "🌦 Погода Брусилів")
async def weather_handler(message: types.Message):
    if PROMETHEUS_AVAILABLE:
        COMMAND_COUNTER.labels(command_type='weather').inc()
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Brusyliv&appid={WEATHER_KEY}&units=metric&lang=ua"
        data = requests.get(url).json()
        temp = data["main"]["temp"]
        await message.answer(f"🌡 Температура: {temp}°C")
    except Exception as e:
        await message.answer(f"⚠️ Помилка погоди: {e}")

@dp.message()
async def ai_chat(message: types.Message):
    if PROMETHEUS_AVAILABLE:
        COMMAND_COUNTER.labels(command_type='ai_chat').inc()

    if not client:
        await message.answer(f"⛔ AI не працює. Причина: {AI_STATUS}")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    start_time = time.time()
    try:
        # 1. ЗАПИТ
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": message.text}],
            model="llama3-8b-8192", 
        )
        response_text = chat_completion.choices[0].message.content
        
        # 2. МЕТРИКА
        if PROMETHEUS_AVAILABLE:
            AI_LATENCY.observe(time.time() - start_time)

        # 3. ВІДПОВІДЬ
        await message.answer(response_text)

    except Exception as e:
        # 4. ОБРОБКА ПОМИЛКИ
        if PROMETHEUS_AVAILABLE:
            ERROR_COUNTER.labels(error_type='groq_error').inc()
        await message.answer(f"🤯 Помилка запиту до Groq: {e}")

async def main():
    if PROMETHEUS_AVAILABLE:
        try:
            start_http_server(8000)
        except:
            pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())