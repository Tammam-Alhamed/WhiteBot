# 🤖 WhiteBot — Advanced Telegram Automation & Digital Commerce Engine

An enterprise-grade, highly scalable Telegram bot built with **Python** and **Asyncio**. WhiteBot is designed to fully automate digital commerce workflows, offering seamless product distribution, dynamic subscription management, and comprehensive administrative analytics.

## 🚀 Core Engineering Features

* **Automated E-Commerce System:** A robust shop engine handling dynamic product catalogs, automated order processing, and user deposit tracking via a secure wallet system.
* **Asynchronous Background Processing:** Leveraged `asyncio` for non-blocking operations, including automated scheduled tasks and real-time notifications (`background_tasks.py` & `scheduler.py`).
* **Automated PDF Reporting:** Engineered a custom reporting module (`pdf_builder.py`) that aggregates complex database metrics and automatically generates daily/weekly PDF sales reports for administrators.
* **Custom Middlewares:** Implemented sophisticated middlewares for user subscription verification, rate-limiting, and application maintenance modes (`subscription.py`, `maintenance.py`).
* **Advanced Admin Dashboard:** A fully functional administrative control panel within Telegram, allowing for real-time monitoring of user activity, financial deposits, and order lifecycles.

## 🏗 Architectural Overview

The project is structured following modular backend best practices to ensure maintainability and high cohesion:
- `bot/middlewares/` - Intercepts and processes updates (e.g., Auth, Subscription limits).
- `handlers/` - Separated domains for `admin`, `shop`, and `common` interactions.
- `services/` - Core business logic, `api_manager`, and `database` interactions.
- `reports/` - Dedicated engine for data aggregation and dynamic PDF generation.
- `states/` - Finite State Machine (FSM) configurations for complex multi-step user conversations.

## 🛠 Tech Stack

* **Language:** Python 3.x
* **Framework:** Aiogram (Asynchronous Telegram Bot API)
* **Database:** SQLite / JSON-based structured storage
* **Asynchronous Programming:** Asyncio
* **Document Generation:** PDF rendering libraries

## 🤝 Contact

**Tammam Alhamed**
* **Role:** Full-Stack Mobile Engineer | Web3 & AI Automation Expert
* **Email:** alhamdtmam@gmail.com
* **Location:** Syria
