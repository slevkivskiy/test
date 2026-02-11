# Беремо легкий Python
FROM python:3.10-slim

# Робоча папка всередині контейнера
WORKDIR /app

# Копіюємо список покупок і ставимо бібліотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо сам код
COPY . .

# Запускаємо бота
CMD ["python", "bot.py"]