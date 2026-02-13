import asyncio
import logging
import os
import time
import requests # <--- ЦЕ ТРЕБА ДЛЯ ПОГОДИ
import asyncpg
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
MODEL_NAME = "llama-3.3-70b-versatile"

# Дані для бази (беруться з .env)
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = "db"  # Ім'я контейнера з docker-compose!

# --- 3. МЕТРИКИ ---
if PROMETHEUS_AVAILABLE:
    COMMAND_COUNTER = Counter('bot_commands_total', 'Total commands', ['command_type'])
    ERROR_COUNTER = Counter('bot_errors_total', 'Total errors', ['error_type'])
    AI_LATENCY = Summary('bot_ai_latency_seconds', 'AI processing time')

# --- 4. НАЛАШТУВАННЯ AI ---
client = None
if GROQ_LIB_OK and AI_KEY:
    try:
        client = Groq(api_key=AI_KEY)
    except Exception:
        pass

# --- 5. БАЗА ДАНИХ (ЛОГІКА) ---
db_pool = None

async def init_db():
    global db_pool
    # Чекаємо поки база прокинеться (10 сек)
    await asyncio.sleep(5)
    try:
        db_pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASS, database=DB_NAME, host=DB_HOST
        )
        # Створюємо таблицю, якщо її немає (АВТОМАТИЧНО!)
        async with db_pool.acquire() as connection:
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE,
                    username TEXT,
                    first_seen TIMESTAMP DEFAULT NOW()
                );
            ''')
        logging.info("✅ База даних підключена і таблиця перевірена.")
    except Exception as e:
        logging.error(f"❌ Помилка БД: {e}")

async def save_user(user: types.User):
    if not db_pool: return
    try:
        async with db_pool.acquire() as connection:
            await connection.execute('''
                INSERT INTO users (telegram_id, username) 
                VALUES ($1, $2) 
                ON CONFLICT (telegram_id) DO NOTHING
            ''', user.id, user.username or "NoName")
    except Exception as e:
        logging.error(f"Не вдалося зберегти юзера: {e}")

# --- 6. БОТ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌦 Погода Брусилів")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await save_user(message.from_user)
    if PROMETHEUS_AVAILABLE: COMMAND_COUNTER.labels(command_type='start').inc()
    await message.answer(f"Привіт! Я записую тебе в базу... 📝\nГотовий до роботи!", reply_markup=kb)

# --- ОСЬ ТУТ Я ПОВЕРНУВ ЛОГІКУ ПОГОДИ ---
@dp.message(F.text == "🌦 Погода Брусилів")
async def weather_handler(message: types.Message):
    await save_user(message.from_user)
    if PROMETHEUS_AVAILABLE: COMMAND_COUNTER.labels(command_type='weather').inc()
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Brusyliv&appid={WEATHER_KEY}&units=metric&lang=ua"
        data = requests.get(url).json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        await message.answer(f"🌡 Температура зараз: {temp}°C\n☁️ {desc.capitalize()}")
    except Exception as e:
        await message.answer(f"⚠️ Помилка погоди: {e}")

@dp.message()
async def ai_chat(message: types.Message):
    await save_user(message.from_user)
    if PROMETHEUS_AVAILABLE: COMMAND_COUNTER.labels(command_type='ai_chat').inc()
    
    if not client:
        await message.answer("AI спить.")
        return

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ти корисний помічник. Відповідай українською."},
                {"role": "user", "content": message.text}
            ],
            model=MODEL_NAME,
            temperature=0.3
        )
        await message.answer(chat_completion.choices[0].message.content)
    except Exception as e:
        await message.answer("Помилка AI.")

async def main():
    if PROMETHEUS_AVAILABLE:
        try:
            start_http_server(8000)
        except: pass
    
    await init_db()  # <--- ЗАПУСК БАЗИ
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())