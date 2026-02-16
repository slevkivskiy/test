import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from typing import Optional

# Замінили requests на aiohttp (щоб бот не зависав під час запиту погоди)
import aiohttp
import asyncpg
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Спроба імпорту метрик та AI (Fault Tolerance)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from prometheus_client import start_http_server, Counter, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# --- 1. НАЛАШТУВАННЯ ЛОГУВАННЯ (Професійний формат) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 2. КОНФІГУРАЦІЯ (Data Class pattern) ---
@dataclass
class Config:
    token: str
    weather_key: Optional[str]
    ai_key: Optional[str]
    db_user: str
    db_pass: str
    db_name: str
    db_host: str

    @staticmethod
    def load_from_env() -> "Config":
        load_dotenv()
        token = os.getenv("BOT_TOKEN")
        if not token:
            logger.critical("❌ BOT_TOKEN не знайдено! Зупинка.")
            sys.exit(1)
        
        return Config(
            token=token,
            weather_key=os.getenv("WEATHER_API_KEY"),
            ai_key=os.getenv("AI_KEY"),
            db_user=os.getenv("DB_USER", "postgres"),
            db_pass=os.getenv("DB_PASSWORD", "password"),
            db_name=os.getenv("POSTGRES_DB", "bot_db"),
            db_host="db"  # Ім'я сервісу в Docker Compose
        )

# --- 3. КЛАС ДЛЯ РОБОТИ З БД (Encapsulation) ---
class Database:
    def __init__(self, config: Config):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Створення пулу з'єднань з ретраями"""
        for i in range(5):
            try:
                self.pool = await asyncpg.create_pool(
                    user=self.config.db_user,
                    password=self.config.db_pass,
                    database=self.config.db_name,
                    host=self.config.db_host
                )
                await self.create_tables()
                logger.info("✅ База даних успішно підключена.")
                return
            except Exception as e:
                logger.warning(f"⚠️ Спроба {i+1}/5 підключення до БД невдала: {e}")
                await asyncio.sleep(5)
        logger.error("❌ Не вдалося підключитися до БД після 5 спроб.")

    async def create_tables(self):
        if not self.pool: return
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE,
                    username TEXT,
                    first_seen TIMESTAMP DEFAULT NOW()
                );
            ''')

    async def save_user(self, user: types.User):
        if not self.pool: return
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO users (telegram_id, username) 
                    VALUES ($1, $2) 
                    ON CONFLICT (telegram_id) DO NOTHING
                ''', user.id, user.username or "NoName")
        except Exception as e:
            logger.error(f"DB Save Error: {e}")

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("🔒 З'єднання з БД закрито.")

# --- 4. МЕТРИКИ (Prometheus) ---
class Metrics:
    def __init__(self):
        if PROMETHEUS_AVAILABLE:
            self.command_counter = Counter('bot_commands_total', 'Total commands', ['command_type'])
            self.error_counter = Counter('bot_errors_total', 'Total errors', ['error_type'])
            self.ai_latency = Summary('bot_ai_latency_seconds', 'AI processing time')
            start_http_server(8000)
            logger.info("📊 Prometheus метрики доступні на порту 8000")

    def track_command(self, command: str):
        if PROMETHEUS_AVAILABLE:
            self.command_counter.labels(command_type=command).inc()

    def track_error(self, error_type: str):
        if PROMETHEUS_AVAILABLE:
            self.error_counter.labels(error_type=error_type).inc()

# --- ІНІЦІАЛІЗАЦІЯ ---
config = Config.load_from_env()
db = Database(config)
metrics = Metrics()
bot = Bot(token=config.token)
dp = Dispatcher()
ai_client = Groq(api_key=config.ai_key) if (GROQ_AVAILABLE and config.ai_key) else None

# Клавіатура
kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌦 Погода Брусилів")]],
    resize_keyboard=True,
    input_field_placeholder="Обери дію або запитай щось..."
)

# --- 5. ХЕНДЛЕРИ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    metrics.track_command('start')
    await db.save_user(message.from_user)
    await message.answer(
        f"👋 Привіт, {message.from_user.first_name}!\nЯ AI-бот з повним DevOps-обвісом.\nЗапитай мене щось або тисни кнопку.", 
        reply_markup=kb
    )

@dp.message(F.text == "🌦 Погода Брусилів")
async def weather_handler(message: types.Message):
    metrics.track_command('weather')
    await db.save_user(message.from_user)
    
    if not config.weather_key:
        await message.answer("⚠️ API ключ погоди не налаштовано.")
        return

    url = f"http://api.openweathermap.org/data/2.5/weather?q=Brusyliv&appid={config.weather_key}&units=metric&lang=ua"

    # 🔥 SENIOR FIX: Використовуємо aiohttp замість requests
    # requests.get() блокує весь бот, поки чекає відповіді.
    # aiohttp робить це асинхронно.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await message.answer("Не вдалося отримати погоду.")
                    return
                data = await response.json()
                
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        await message.answer(f"🌡 У Брусилові зараз: {temp}°C\n☁️ {desc.capitalize()}")
        
    except Exception as e:
        logger.error(f"Weather API Error: {e}")
        metrics.track_error('weather_api')
        await message.answer("⚠️ Помилка при отриманні погоди.")

@dp.message()
async def ai_chat(message: types.Message):
    metrics.track_command('ai_chat')
    await db.save_user(message.from_user)

    if not ai_client:
        await message.answer("🧠 AI модуль вимкнено або не налаштовано.")
        return

    processing_msg = await message.answer("⏳ Думаю...")
    
    try:
        # Вимір часу відповіді AI для Grafana
        start_time = asyncio.get_event_loop().time()
        
        # Groq виклик (він синхронний, тому запускаємо в окремому потоці, щоб не блокувати)
        chat_completion = await asyncio.to_thread(
            ai_client.chat.completions.create,
            messages=[
                {"role": "system", "content": "Ти корисний помічник. Відповідай українською лаконічно."},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3
        )
        
        duration = asyncio.get_event_loop().time() - start_time
        if PROMETHEUS_AVAILABLE:
             metrics.ai_latency.observe(duration)

        response_text = chat_completion.choices[0].message.content
        await processing_msg.edit_text(response_text)

    except Exception as e:
        logger.error(f"AI Error: {e}")
        metrics.track_error('ai_api')
        await processing_msg.edit_text("🤯 Щось пішло не так з AI.")

# --- 6. ЗАПУСК ---
async def main():
    logger.info("🚀 Запуск бота...")
    
    # Підключення до БД
    await db.connect()
    
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")