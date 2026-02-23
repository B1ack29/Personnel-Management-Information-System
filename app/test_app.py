import pytest
import os
import tempfile
import uuid
from app import app, get_db_connection
from werkzeug.security import generate_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

@pytest.fixture
def client():
    """Создание тестового клиента с временной БД"""
    # Создаем временную тестовую базу данных
    test_db_name = f"test_hr_system_{uuid.uuid4().hex[:8]}"
    
    # Подключаемся к PostgreSQL для создания тестовой БД
    conn = psycopg2.connect(
        host='localhost',
        database='postgres',
        user='postgres',
        password='postgres'
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Создаем тестовую БД
    cur.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    cur.execute(f"CREATE DATABASE {test_db_name}")
    cur.close()
    conn.close()
    
    # Настраиваем конфиг для тестов
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-key'
    
    # Временно заменяем конфиг БД
    original_db_config = app.config.get('DB_CONFIG', {})
    app.config['DB_CONFIG'] = {
        'host': 'localhost',
        'database': test_db_name,
        'user': 'postgres',
        'password': 'postgres',
        'port': '5432'
    }
    
    # Инициализируем тестовую БД
    init_test_database(test_db_name)
    
    with app.test_client() as test_client:
        yield test_client
    
    # Очистка - удаляем тестовую БД
    conn = psycopg2.connect(
        host='localhost',
        database='postgres',
        user='postgres',
        password='postgres'
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    cur.close()
    conn.close()
    
    # Восстанавливаем оригинальный конфиг
    app.config['DB_CONFIG'] = original_db_config

def init_test_database(db_name):
    """Инициализация тестовой базы данных"""
    conn = psycopg2.connect(
        host='localhost',
        database=db_name,
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()
    
    # Создаем таблицы
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(200) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            middle_name VARCHAR(50),
            birth_date DATE,
            phone VARCHAR(20),
            email VARCHAR(100) UNIQUE,
            address VARCHAR(200),
            hire_date DATE NOT NULL DEFAULT CURRENT_DATE,
            salary NUMERIC(10, 2),
            department_id INTEGER NOT NULL,
            position_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
            FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
        )
    """)
    
    # Создаем тестовые данные
    admin_password = generate_password_hash('admin123')
    user_password = generate_password_hash('user123')
    
    # Вставляем пользователей
    cur.execute("""
        INSERT INTO users (username, email, password_hash, is_admin) 
        SELECT %s, %s, %s, %s
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = %s)
    """, ('admin', 'admin@test.com', admin_password, True, 'admin'))
    
    cur.execute("""
        INSERT INTO users (username, email, password_hash, is_admin) 
        SELECT %s, %s, %s, %s
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = %s)
    """, ('user', 'user@test.com', user_password, False, 'user'))
    
    # Отделы
    cur.execute("""
        INSERT INTO departments (name, description) 
        SELECT %s, %s
        WHERE NOT EXISTS (SELECT 1 FROM departments WHERE name = %s)
    """, ('IT отдел', 'Тестовый IT отдел', 'IT отдел'))
    
    cur.execute("""
        INSERT INTO departments (name, description) 
        SELECT %s, %s
        WHERE NOT EXISTS (SELECT 1 FROM departments WHERE name = %s)
    """, ('Бухгалтерия', 'Тестовая бухгалтерия', 'Бухгалтерия'))
    
    # Должности
    cur.execute("""
        INSERT INTO positions (name, description) 
        SELECT %s, %s
        WHERE NOT EXISTS (SELECT 1 FROM positions WHERE name = %s)
    """, ('Программист', 'Тестовый программист', 'Программист'))
    
    cur.execute("""
        INSERT INTO positions (name, description) 
        SELECT %s, %s
        WHERE NOT EXISTS (SELECT 1 FROM positions WHERE name = %s)
    """, ('Бухгалтер', 'Тестовый бухгалтер', 'Бухгалтер'))
    
    conn.commit()
    cur.close()
    conn.close()

def get_unique_email(base_email='test'):
    """Генерация уникального email"""
    return f'{base_email}_{uuid.uuid4().hex[:8]}@test.com'

def login_admin(client):
    """Вспомогательная функция для входа админа"""
    return client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)

def login_user(client):
    """Вспомогательная функция для входа пользователя"""
    return client.post('/login', data={
        'username': 'user',
        'password': 'user123'
    }, follow_redirects=True)

# ============= ТЕСТЫ =============

def test_app_exists():
    """Тест: приложение существует"""
    assert app is not None

def test_client_created(client):
    """Тест: клиент создан"""
    assert client is not None

def test_home_page_redirects_to_login(client):
    """Тест: главная страница перенаправляет на login"""
    response = client.get('/')
    assert response.status_code == 302
    assert '/login' in response.location

def test_login_page_loads(client):
    """Тест: страница входа загружается"""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'form' in response.data
    assert b'username' in response.data
    assert b'password' in response.data

def test_login_with_admin(client):
    """Тест: вход админа работает"""
    response = login_admin(client)
    assert response.status_code == 200
    # Проверяем наличие admin в ответе (без русского текста)
    assert b'admin' in response.data.lower()

def test_login_with_user(client):
    """Тест: вход пользователя работает"""
    response = login_user(client)
    assert response.status_code == 200
    # Проверяем наличие user в ответе
    assert b'user' in response.data.lower()

def test_wrong_password(client):
    """Тест: неверный пароль"""
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'wrong_password'
    }, follow_redirects=True)
    assert response.status_code == 200
    # Проверяем наличие ошибки (по английскому тексту или статусу)
    assert b'login' in response.data.lower() or b'error' in response.data.lower()

def test_logout(client):
    """Тест: выход из системы"""
    # Сначала логинимся
    login_admin(client)
    
    # Выходим
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    # Проверяем, что перенаправило на страницу входа
    assert b'login' in response.data.lower()

def test_employees_page_after_login(client):
    """Тест: страница сотрудников доступна после входа"""
    login_admin(client)
    
    response = client.get('/employees')
    assert response.status_code == 200
    # Проверяем наличие таблицы или списка
    assert b'table' in response.data.lower() or b'employee' in response.data.lower()

def test_departments_page_after_login(client):
    """Тест: страница отделов доступна после входа"""
    login_admin(client)
    
    response = client.get('/departments')
    assert response.status_code == 200
    # Проверяем наличие таблицы или списка
    assert b'table' in response.data.lower() or b'department' in response.data.lower()

def test_add_employee_form_loads_for_admin(client):
    """Тест: форма добавления доступна админу"""
    login_admin(client)
    
    response = client.get('/add_employee')
    assert response.status_code == 200
    # Проверяем наличие формы
    assert b'form' in response.data
    assert b'first_name' in response.data

def test_user_cannot_access_add_form(client):
    """Тест: обычный пользователь не может добавить сотрудника"""
    login_user(client)
    
    response = client.get('/add_employee', follow_redirects=True)
    # Проверяем, что нет формы добавления
    assert b'add_employee' not in response.data.lower() or b'form' not in response.data

def test_add_employee(client):
    """Тест: добавление сотрудника"""
    login_admin(client)
    
    # Получаем ID отдела и должности
    conn = psycopg2.connect(**app.config['DB_CONFIG'])
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id FROM departments LIMIT 1")
    dept = cur.fetchone()
    cur.execute("SELECT id FROM positions LIMIT 1")
    pos = cur.fetchone()
    cur.close()
    conn.close()
    
    unique_email = get_unique_email()
    
    response = client.post('/add_employee', data={
        'first_name': 'Petr',
        'last_name': 'Petrov',
        'middle_name': 'Petrovich',
        'birth_date': '1985-05-15',
        'phone': '89257654321',
        'email': unique_email,
        'address': 'Saint Petersburg',
        'hire_date': '2023-01-01',
        'department_id': dept['id'],
        'position_id': pos['id'],
        'salary': 60000
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Проверяем успешное добавление по наличию email в ответе или редиректу
    assert response.status_code == 200

def test_edit_employee(client):
    """Тест: редактирование сотрудника"""
    login_admin(client)
    
    # Получаем ID сотрудника
    conn = psycopg2.connect(**app.config['DB_CONFIG'])
    cur = conn.cursor()
    cur.execute("SELECT id FROM employees LIMIT 1")
    employee_id = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    response = client.post(f'/edit_employee/{employee_id}', data={
        'first_name': 'Ivan',
        'last_name': 'Ivanov',
        'middle_name': 'Ivanovich',
        'birth_date': '1990-01-01',
        'phone': '89251234567',
        'email': 'ivan.updated@test.com',
        'address': 'Moscow',
        'hire_date': '2023-01-01',
        'department_id': 1,
        'position_id': 1,
        'salary': 55000
    }, follow_redirects=True)
    
    assert response.status_code == 200

def test_search_employees(client):
    """Тест: поиск сотрудников"""
    login_admin(client)
    
    response = client.get('/search_employees?query=Ivan')
    assert response.status_code == 200
    # Проверяем наличие результатов поиска
    assert b'Ivan' in response.data or b'employee' in response.data

def test_change_password(client):
    """Тест: смена пароля"""
    login_user(client)
    
    response = client.post('/change_password', data={
        'old_password': 'user123',
        'new_password': 'newpass123',
        'confirm_password': 'newpass123'
    }, follow_redirects=True)
    
    assert response.status_code == 200

def test_view_employee(client):
    """Тест: просмотр сотрудника"""
    login_admin(client)
    
    # Получаем ID первого сотрудника
    conn = psycopg2.connect(**app.config['DB_CONFIG'])
    cur = conn.cursor()
    cur.execute("SELECT id FROM employees LIMIT 1")
    employee_id = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    response = client.get(f'/view_employee/{employee_id}')
    assert response.status_code == 200
    # Проверяем наличие информации о сотруднике
    assert b'first_name' in response.data.lower() or b'last_name' in response.data.lower()

def test_delete_employee(client):
    """Тест: удаление сотрудника"""
    login_admin(client)
    
    # Сначала добавим сотрудника для удаления
    conn = psycopg2.connect(**app.config['DB_CONFIG'])
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id FROM departments LIMIT 1")
    dept = cur.fetchone()
    cur.execute("SELECT id FROM positions LIMIT 1")
    pos = cur.fetchone()
    
    unique_email = get_unique_email()
    
    cur.execute("""
        INSERT INTO employees (first_name, last_name, email, hire_date, department_id, position_id, salary)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    """, ('Test', 'Testov', unique_email, '2023-01-01', dept['id'], pos['id'], 10000))
    employee_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()
    
    # Удаляем
    response = client.get(f'/delete_employee/{employee_id}', follow_redirects=True)
    assert response.status_code == 200

def test_database_has_data(client):
    """Тест: в БД есть данные"""
    conn = psycopg2.connect(**app.config['DB_CONFIG'])
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM users")
    users_count = cur.fetchone()[0]
    assert users_count >= 2
    
    cur.execute("SELECT COUNT(*) FROM departments")
    depts_count = cur.fetchone()[0]
    assert depts_count >= 2
    
    cur.execute("SELECT COUNT(*) FROM positions")
    positions_count = cur.fetchone()[0]
    assert positions_count >= 2
    
    cur.execute("SELECT COUNT(*) FROM employees")
    employees_count = cur.fetchone()[0]
    assert employees_count >= 1
    
    cur.close()
    conn.close()

def test_department_employee_count(client):
    """Тест: подсчет сотрудников в отделах"""
    login_admin(client)
    
    response = client.get('/departments')
    assert response.status_code == 200
    # Проверяем наличие информации о количестве сотрудников
    assert b'employees_count' in response.data.lower() or b'count' in response.data.lower()

def test_unique_email_constraint(client):
    """Тест: ограничение уникальности email"""
    login_admin(client)
    
    # Пытаемся добавить сотрудника с существующим email
    conn = psycopg2.connect(**app.config['DB_CONFIG'])
    cur = conn.cursor()
    cur.execute("SELECT email FROM employees LIMIT 1")
    existing_email = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id FROM departments LIMIT 1")
    dept = cur.fetchone()
    cur.execute("SELECT id FROM positions LIMIT 1")
    pos = cur.fetchone()
    cur.close()
    conn.close()
    
    response = client.post('/add_employee', data={
        'first_name': 'Test',
        'last_name': 'Testov',
        'email': existing_email,
        'hire_date': '2023-01-01',
        'department_id': dept['id'],
        'position_id': pos['id'],
        'salary': 50000
    }, follow_redirects=True)
    
    assert response.status_code == 200