# 1. Використовуємо конкретну версію та slim для ваги
FROM python:3.11-slim

# 2. Встановлюємо змінні середовища, щоб Python не тупив
# PYTHONDONTWRITEBYTECODE — не плодить .pyc файли в контейнері
# PYTHONUNBUFFERED — щоб логи бота летіли в консоль миттєво
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 3. Створюємо системного користувача (БЕЗПЕКА №1)
# За замовчуванням Docker ранить усе від root. Це дірка в безпеці.
RUN useradd -m myuser && chown -R myuser /app

# 4. Копіюємо requirements і ставимо залежності
COPY --chown=myuser:myuser requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Копіюємо код під нашим юзером
COPY --chown=myuser:myuser . .

# 6. Перемикаємося на безпечного юзера
USER myuser

CMD ["python", "bot.py"]