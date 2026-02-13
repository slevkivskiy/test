# 🤖 AI Assistant Bot (Pet Project)

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![AI](https://img.shields.io/badge/AI-Llama_3.3-orange)
![Monitoring](https://img.shields.io/badge/Monitoring-Prometheus_Grafana-red)

Цей проект — Telegram-бот з інтеграцією штучного інтелекту (Llama 3.3 через Groq API), розгорнутий у контейнеризованому середовищі з повним стеком моніторингу.

## 🚀 Функціонал
- **AI Chat:** Спілкування з LLM Llama 3.3 (70B) українською мовою.
- **Tools:** Отримання погоди через OpenWeatherMap API.
- **DevOps:** Автоматичний перезапуск, логування помилок.
- **Monitoring:** Збір метрик (RPS, Latency, Errors) через Prometheus.

## 🛠 Технологічний стек
| Компонент | Технологія | Опис |
|-----------|------------|------|
| **Core** | Python 3.11, Aiogram 3 | Основна логіка бота (асинхронна) |
| **AI Engine** | Groq API (Llama 3.3) | Швидка генерація відповідей |
| **Containerization** | Docker, Docker Compose | Ізоляція середовища та залежностей |
| **Metrics** | Prometheus | Збір технічних та бізнес-метрик |
| **Visualization** | Grafana | Дашборди для моніторингу стану бота |

## ⚙️ Як запустити (Local / VPS)

### 1. Клонування репозиторію
```bash
git clone https://github.com/slevkivskiy/test.git
cd test