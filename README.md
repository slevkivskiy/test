# 🚀 AI Telegram Bot with DevOps Observability Stack

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-EC2-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-Visualization-F46800?style=for-the-badge&logo=grafana&logoColor=white)

Цей проект — це демонстрація **Production-Ready** інфраструктури для Telegram бота.
Реалізовано повний цикл DevOps практик: від **Infrastructure as Code (IaC)** до налаштування **SSL**, **Reverse Proxy** та системи **Alerting**.

---

## 🏗️ Архітектура

Весь проект розгорнуто на хмарі **AWS (EC2)**, інфраструктура описана через **Terraform**. Трафік проходить через **Cloudflare** (CDN/WAF) та обробляється **Nginx**.

```mermaid
graph TD
    User((Користувач)) -->|HTTPS| CF[Cloudflare Proxy]
    CF -->|SSL/443| Nginx[Nginx Reverse Proxy]
    
    subgraph "AWS EC2 (Docker Compose Network)"
        Nginx -->|Proxy| Bot["AI Bot (Python/Aiogram)"]
        Nginx -->|Proxy| Grafana["Grafana Dashboard"]
        Bot -->|Metrics| Prom[Prometheus]
        Prom -->|Scrape| NodeExp[Node Exporter]
        Prom -->|Alerts| TG_Alerts[Telegram Alerts]
    end
