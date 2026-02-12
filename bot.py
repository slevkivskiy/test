import asyncio
import logging
import os
import time
import requests
from groq import Groq
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- МЕТРИКИ ---
try:
    from prometheus_client import start_http_server, Counter, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# --- 1. КОНФІГ ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_API_KEY")

# 👇 ТУТ Я ЗМІНИВ НАЗВУ: ТЕПЕР ВІН ШУКАЄ "AI_KEY"
GROQ_KEY = os.getenv("AI_KEY") 

# --- 2. МЕТРИКИ ---
if PROMETHEUS_AVAILABLE:
    COMMAND_COUNTER = Counter('bot_commands_total', 'Total commands', ['command_type'])
    ERROR_COUNTER = Counter('bot_errors_total', 'Total errors', ['error_type'])
    AI_LATENCY = Summary('bot_ai_latency_seconds', 'AI processing time')

# --- 3. ПІДКЛЮЧЕННЯ GROQ ---
client = None
if GROQ_KEY:
    try:
        client = Groq(api_key=GROQ_KEY)
        print("✅ Groq (Llama 3) підключено через AI_KEY!")
    except Exception as e:
        print(f"❌ Помилка ключа AI_KEY: {e}")
else:
    print("❌ ЗМІННА 'AI_KEY' НЕ ЗНАЙДЕНА В .env!")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌦 Погода Брусилів")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if PROMETHEUS_AVAILABLE:
        COMMAND_COUNTER.labels(command_type='start').inc()
    await message.answer("Llama 3 на зв'язку! 🚀", reply_markup=kb)

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
        await message.answer("❌ AI_KEY не знайдено або не працює.")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    start_time = time.time()
    try:
        # ЗАПИТ ДО GROQ
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": message.text,
                }
            ],
            model="llama3-8b-8192", 
        )
        
        response_text = chat_completion.choices[0].message.content

        if PROMETHEUS_AVAILABLE:
            AI_LATENCY.observe(time.time() - start_time)