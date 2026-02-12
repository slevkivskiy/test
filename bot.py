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

# --- МЕТРИКИ (Без падіння, якщо немає ліби) ---
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
    COMMAND_COUNTER = Counter('bot_commands_total', 'Total commands', ['command_type'])
    ERROR_COUNTER = Counter('bot_errors_total', 'Total errors', ['error_type'])
    AI_LATENCY = Summary('bot_ai_latency_seconds', 'AI processing time')
    WEATHER_LATENCY = Summary('bot_weather_latency_seconds', 'Weather fetch time')

# --- 3. НЕПРОБИВНЕ ПІДКЛЮЧЕННЯ AI ---
model = None

def force_connect_ai():
    global model
    if not GEMINI_KEY:
        print("❌ Ключа немає!")
        return

    try:
        genai.configure(api_key=GEMINI_KEY)
        
        # СПИСОК НАДІЇ: Пробуємо по черзі
        candidates = [
            'gemini-1.5-flash', # Найкраща
            'gemini-1.5-flash-001', # Стабільна версія
            'gemini-pro',       # Стара добра (завжди працює)
            'gemini-1.0-pro'    # Альтернативна назва старої
        ]
        
        for candidate in candidates:
            try:
                print(f"🔄 Пробую підключити: {candidate}...")
                test_model = genai.GenerativeModel(candidate)
                # Тестовий пінг (генерація 1 токена), щоб перевірити чи працює
                test_model.generate_content("Hi") 
                
                # Якщо дійшли сюди - модель робоча!
                model = test_model
                print(f"✅ УСПІХ! Працюємо на: {candidate}")
                return
            except Exception as e:
                print(f"⚠️ {candidate} не підійшла: {e}")
                continue
        
        print("❌ Жодна модель не запустилась. Це фіаско.")

    except Exception as e:
        print(f"💀 Критична помилка AI: {e}")

# Запускаємо підбір
force_connect_ai()

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
    await message.answer("Бот перезавантажено. Режим виживання активовано. 🛡", reply_markup=kb)

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
        await message.answer("❌ AI здох остаточно. Дивись логи.")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    start_time = time.time()
    try:
        response = model.generate_content(message.text)
        
        if PROMETHEUS_AVAILABLE:
            AI_LATENCY.observe(time.time() - start_time)
        
        await message.answer(response.text)
        
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            if PROMETHEUS_AVAILABLE:
                ERROR_COUNTER.labels(error_type='ai_rate_limit').inc()
            await message.answer("⏳ Ліміт. Почекай трохи.")
        else:
            if PROMETHEUS_AVAILABLE:
                ERROR_COUNTER.labels(error_type='ai_error').inc()
            await message.answer(f"Error: {err_msg}")

async def main():
    if PROMETHEUS_AVAILABLE:
        start_http_server(8000)
        logging.info("🔥 Metrics server running on port 8000")
        
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())