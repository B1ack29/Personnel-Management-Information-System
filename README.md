# 👥 Personnel Management Information System

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0+-lightgrey?style=for-the-badge&logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-blue?style=for-the-badge&logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

> Веб-приложение для автоматизации управления кадрами (HR-система)

---

## 📋 О проекте

Простая и удобная HR-система для учета сотрудников, отделов и должностей с разграничением прав доступа.

### ✨ Возможности

| Роль | Действия |
|------|----------|
| **Пользователь** | • Просмотр сотрудников и отделов<br>• Поиск по базе<br>• Детальная информация<br>• Смена пароля |
| **Администратор** | • Всё что у пользователя<br>• Добавление сотрудников<br>• Редактирование данных<br>• Удаление записей<br>• Управление отделами |

---

## 🛠 Технологии

---

## 🚀 Быстрый старт

```bash
# 1. Клонируем
git clone https://github.com/your-username/Personnel-Management-Information-System.git
cd Personnel-Management-Information-System

# 2. Виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Зависимости
pip install Flask psycopg2-binary pytest Werkzeug

# 4. Создайте БД в PostgreSQL
# 5. Запустите инициализацию
python -c "from app import init_database; init_database()"

# 6. Запуск
python app.py