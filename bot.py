import asyncio
import logging
import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. Завантажуємо змінні
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# 2. Налаштовуємо Gemini (якщо є ключ)
model = None
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    # Використовуємо швидку і розумну модель
    model = genai.GenerativeModel('gemini-pro')

# 3. Налаштовуємо Бота
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВІАТУРА ---
kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌦 Погода Брусилів")],
        [KeyboardButton(text="💀 Знищити сервер (Жарт)")]
    ],
    resize_keyboard=True
)

# --- КОМАНДИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привіт! Я DevOps-бот з мізками Gemini! 🤖\n"
        "Тисни кнопки або просто запитай мене про щось (наприклад, 'Як підняти Docker?').", 
        reply_markup=kb
    )

# --- ПОГОДА ---
@dp.message(F.text == "🌦 Погода Брусилів")
async def weather_handler(message: types.Message):
    if not WEATHER_KEY:
        await message.answer("❌ Немає ключа погоди!")
        return
        
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Brusyliv&appid={WEATHER_KEY}&units=metric&lang=ua"
        data = requests.get(url).json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        await message.answer(f"Погода в Брусилові:\n🌡 {temp}°C, {desc}")
    except:
        await message.answer("⚠️ Не можу отримати погоду.")

# --- GEMINI AI (Обробляє все інше) ---
@dp.message()
async def chat_handler(message: types.Message):
    # 1. Перевірка наявності мізків
    if not model:
        await message.answer("🧠 Я забув свій API ключ вдома. Перевір .env!")
        return

    # 2. Показуємо статус "друкує..."
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # 3. Питаємо Gemini
        response = model.generate_content(message.text)
        
        # 4. Відправляємо відповідь (Markdown для красивого коду)
        await message.answer(response.text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"🤯 У мене закипіли мізки: {e}")

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())