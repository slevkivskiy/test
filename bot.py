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

# --- СПРОБА ІМПОРТУ МЕТРИК ---
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

# --- 3. РОЗУМНИЙ ВИБІР МОДЕЛІ ---
model = None

def setup_ai():
    global model
    if not GEMINI_KEY:
        print("❌ GEMINI_KEY не знайдено!")
        return

    try:
        genai.configure(api_key=GEMINI_KEY)
        print("🔍 Сканую доступні моделі...")
        
        # Отримуємо список моделей, які підтримують генерацію тексту
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print(f"📋 Доступні моделі: {all_models}")

        # ПРІОРИТЕТИ: Шукаємо стабільні версії 1.5, потім 1.0, потім будь-що
        chosen_model_name = None
        
        # 1. Спробуємо знайти конкретно 1.5-flash (стабільну)
        for m in all_models:
            if 'gemini-1.5-flash' in m and 'latest' not in m and '001' in m: # Шукаємо версію 001 або чисту
                chosen_model_name = m
                break
        
        # 2. Якщо не знайшли, шукаємо будь-яку flash (крім 2.5, бо там ліміти)
        if not chosen_model_name:
            for m in all_models:
                if 'flash' in m and '2.5' not in m:
                    chosen_model_name = m
                    break
        
        # 3. Якщо все ще немає, шукаємо gemini-pro
        if not chosen_model_name:
            for m in all_models:
                if 'gemini-pro' in m:
                    chosen_model_name = m
                    break
                    
        # 4. Якщо зовсім біда - беремо першу зі списку
        if not chosen_model_name and all_models:
            chosen_model_name = all_models[0]

        if chosen_model_name:
            print(f"✅ ВИБРАНО МОДЕЛЬ: {chosen_model_name}")
            model = genai.GenerativeModel(chosen_model_name)
        else:
            print("❌ Не знайдено жодної робочої моделі!")

    except Exception as e:
        print(f"⚠️ Помилка налаштування AI: {e}")

# Запускаємо налаштування
setup_ai()

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
    await message.answer("Бот перезавантажено. Модель підібрана автоматично. 🤖", reply_markup=kb)

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
        await message.answer("❌ AI недоступний. Перевір логи сервера.")
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
            ERROR_COUNTER.labels(error_type='ai_error').inc()
        
        err_msg = str(e)
        if "429" in err_msg:
            await message.answer("⏳ Ліміт запитів вичерпано. Дай мені 30 секунд відпочити.")
        else:
            await message.answer(f"🤯 Помилка AI: {err_msg}")

async def main():
    if PROMETHEUS_AVAILABLE:
        start_http_server(8000)
        logging.info("🔥 Metrics server running on port 8000")
        
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())