Personnel Management Information System
https://img.shields.io/badge/Python-3.8%252B-blue
https://img.shields.io/badge/Flask-2.0%252B-lightgrey
https://img.shields.io/badge/PostgreSQL-12%252B-blue

Веб-приложение для управления кадрами (HR) с разграничением прав доступа.

Возможности
Для всех пользователей:

Просмотр статистики на главной

Список сотрудников и отделов

Поиск сотрудников

Детальная карточка сотрудника

Смена пароля

Для администраторов:

Добавление/редактирование/удаление сотрудников

Управление отделами

Технологии
Backend: Python, Flask, PostgreSQL, pytest

Frontend: HTML5, CSS3, Jinja2

Быстрый старт
Клонировать репозиторий

bash
git clone https://github.com/your-username/Personnel-Management-Information-System.git
cd Personnel-Management-Information-System
Создать виртуальное окружение и установить зависимости

bash
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate для Windows
pip install Flask psycopg2-binary pytest Werkzeug
Настроить PostgreSQL

Создать БД hr_system

Настроить переменные в app.py или через переменные окружения

Инициализировать БД

bash
python -c "from app import init_database; init_database()"
Запустить приложение

bash
python app.py
Доступно по адресу: http://127.0.0.1:5000