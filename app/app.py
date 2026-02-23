from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-12345')

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'hr_system'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'port': os.environ.get('DB_PORT', '5432')
}

def get_db_connection():
    """Получение соединения с базой данных"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        if not session.get('is_admin', False):
            flash('У вас нет прав для выполнения этого действия', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute(
                "SELECT * FROM users WHERE username = %s",
                (username,)
            )
            user = cur.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                
                cur.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                    (user['id'],)
                )
                conn.commit()
                
                flash(f'Добро пожаловать, {user["username"]}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверное имя пользователя или пароль', 'error')
        except Exception as e:
            flash(f'Ошибка входа: {str(e)}', 'error')
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Главная страница"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("SELECT COUNT(*) as count FROM employees")
        total_employees = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM departments")
        total_departments = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM positions")
        total_positions = cur.fetchone()['count']
        
        cur.execute("""
            SELECT e.*, d.name as department_name, p.name as position_name,
                   e.last_name || ' ' || e.first_name || COALESCE(' ' || e.middle_name, '') as full_name,
                   TO_CHAR(e.hire_date, 'DD.MM.YYYY') as hire_date_formatted
            FROM employees e
            JOIN departments d ON e.department_id = d.id
            JOIN positions p ON e.position_id = p.id
            ORDER BY e.hire_date DESC
            LIMIT 5
        """)
        recent_employees = cur.fetchall()
        
        return render_template('index.html',
                             total_employees=total_employees,
                             total_departments=total_departments,
                             total_positions=total_positions,
                             recent_employees=recent_employees)
    finally:
        cur.close()
        conn.close()

@app.route('/employees')
@login_required
def employees():
    """Список сотрудников"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT e.*, d.name as department_name, p.name as position_name,
                   e.last_name || ' ' || e.first_name || COALESCE(' ' || e.middle_name, '') as full_name,
                   TO_CHAR(e.hire_date, 'DD.MM.YYYY') as hire_date_formatted
            FROM employees e
            JOIN departments d ON e.department_id = d.id
            JOIN positions p ON e.position_id = p.id
            ORDER BY e.last_name, e.first_name
        """)
        employees_list = cur.fetchall()
        
        return render_template('employees.html',
                             employees=employees_list,
                             is_admin=session.get('is_admin', False))
    finally:
        cur.close()
        conn.close()

@app.route('/add_employee', methods=['GET', 'POST'])
@login_required
@admin_required
def add_employee():
    """Добавление сотрудника"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if request.method == 'POST':
            cur.execute(
                "SELECT id FROM employees WHERE email = %s",
                (request.form['email'],)
            )
            if cur.fetchone():
                flash('Сотрудник с таким email уже существует', 'error')
                return redirect(url_for('add_employee'))
            
            cur.execute("""
                INSERT INTO employees (
                    first_name, last_name, middle_name, birth_date,
                    phone, email, address, hire_date,
                    department_id, position_id, salary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                request.form['first_name'],
                request.form['last_name'],
                request.form.get('middle_name', ''),
                request.form['birth_date'],
                request.form['phone'],
                request.form['email'],
                request.form.get('address', ''),
                request.form['hire_date'],
                int(request.form['department_id']),
                int(request.form['position_id']),
                float(request.form['salary'])
            ))
            conn.commit()
            flash('Сотрудник успешно добавлен!', 'success')
            return redirect(url_for('employees'))
        
        cur.execute("SELECT * FROM departments ORDER BY name")
        departments = cur.fetchall()
        
        cur.execute("SELECT * FROM positions ORDER BY name")
        positions = cur.fetchall()
        
        return render_template('add_employee.html',
                             departments=departments,
                             positions=positions)
    except Exception as e:
        conn.rollback()
        flash(f'Ошибка: {str(e)}', 'error')
        return redirect(url_for('employees'))
    finally:
        cur.close()
        conn.close()

@app.route('/edit_employee/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(id):
    """Редактирование сотрудника"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if request.method == 'POST':
            cur.execute(
                "SELECT id FROM employees WHERE email = %s AND id != %s",
                (request.form['email'], id)
            )
            if cur.fetchone():
                flash('Сотрудник с таким email уже существует', 'error')
                return redirect(url_for('edit_employee', id=id))
            
            cur.execute("""
                UPDATE employees SET
                    first_name = %s, last_name = %s, middle_name = %s,
                    birth_date = %s, phone = %s, email = %s,
                    address = %s, hire_date = %s,
                    department_id = %s, position_id = %s, salary = %s
                WHERE id = %s
            """, (
                request.form['first_name'],
                request.form['last_name'],
                request.form.get('middle_name', ''),
                request.form['birth_date'],
                request.form['phone'],
                request.form['email'],
                request.form.get('address', ''),
                request.form['hire_date'],
                int(request.form['department_id']),
                int(request.form['position_id']),
                float(request.form['salary']),
                id
            ))
            conn.commit()
            flash('Данные сотрудника обновлены!', 'success')
            return redirect(url_for('employees'))
        
        cur.execute("SELECT * FROM employees WHERE id = %s", (id,))
        employee = cur.fetchone()
        
        if not employee:
            flash('Сотрудник не найден', 'error')
            return redirect(url_for('employees'))
        
        cur.execute("SELECT * FROM departments ORDER BY name")
        departments = cur.fetchall()
        
        cur.execute("SELECT * FROM positions ORDER BY name")
        positions = cur.fetchall()
        
        return render_template('edit_employee.html',
                             employee=employee,
                             departments=departments,
                             positions=positions)
    finally:
        cur.close()
        conn.close()

@app.route('/delete_employee/<int:id>')
@login_required
@admin_required
def delete_employee(id):
    """Удаление сотрудника"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM employees WHERE id = %s", (id,))
        conn.commit()
        flash('Сотрудник удален!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('employees'))

@app.route('/departments')
@login_required
def departments():
    """Список отделов"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT d.*, COUNT(e.id) as employees_count
            FROM departments d
            LEFT JOIN employees e ON d.id = e.department_id
            GROUP BY d.id
            ORDER BY d.name
        """)
        departments_list = cur.fetchall()
        
        return render_template('departments.html',
                             departments=departments_list,
                             is_admin=session.get('is_admin', False))
    finally:
        cur.close()
        conn.close()

@app.route('/add_department', methods=['POST'])
@login_required
@admin_required
def add_department():
    """Добавление отдела"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            "INSERT INTO departments (name, description) VALUES (%s, %s)",
            (request.form['name'], request.form.get('description', ''))
        )
        conn.commit()
        flash('Отдел успешно добавлен!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Ошибка при добавлении отдела: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('departments'))

@app.route('/delete_department/<int:id>')
@login_required
@admin_required
def delete_department(id):
    """Удаление отдела"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT COUNT(*) FROM employees WHERE department_id = %s", (id,))
        count = cur.fetchone()[0]
        
        if count > 0:
            flash('Нельзя удалить отдел, в котором есть сотрудники', 'error')
        else:
            cur.execute("DELETE FROM departments WHERE id = %s", (id,))
            conn.commit()
            flash('Отдел удален!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Ошибка при удалении отдела: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('departments'))

@app.route('/search_employees')
@login_required
def search_employees():
    """Поиск сотрудников"""
    query = request.args.get('query', '')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if query:
            cur.execute("""
                SELECT e.*, d.name as department_name, p.name as position_name,
                       e.last_name || ' ' || e.first_name || COALESCE(' ' || e.middle_name, '') as full_name,
                       TO_CHAR(e.hire_date, 'DD.MM.YYYY') as hire_date_formatted
                FROM employees e
                JOIN departments d ON e.department_id = d.id
                JOIN positions p ON e.position_id = p.id
                WHERE e.first_name ILIKE %s
                   OR e.last_name ILIKE %s
                   OR e.email ILIKE %s
                   OR e.phone ILIKE %s
                ORDER BY e.last_name, e.first_name
            """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
            employees_list = cur.fetchall()
        else:
            employees_list = []
        
        return render_template('search_results.html',
                             employees=employees_list,
                             query=query,
                             is_admin=session.get('is_admin', False))
    finally:
        cur.close()
        conn.close()

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Смена пароля"""
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            
            cur.execute(
                "SELECT * FROM users WHERE id = %s",
                (session['user_id'],)
            )
            user = cur.fetchone()
            
            if not user:
                flash('Пользователь не найден', 'error')
                return redirect(url_for('change_password'))
            
            if not check_password_hash(user['password_hash'], old_password):
                flash('Неверный текущий пароль', 'error')
            elif new_password != confirm_password:
                flash('Новые пароли не совпадают', 'error')
            elif len(new_password) < 4:
                flash('Пароль должен быть не менее 4 символов', 'error')
            else:
                password_hash = generate_password_hash(new_password)
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (password_hash, session['user_id'])
                )
                conn.commit()
                flash('Пароль успешно изменен', 'success')
                return redirect(url_for('index'))
        except Exception as e:
            conn.rollback()
            flash(f'Ошибка при смене пароля: {str(e)}', 'error')
        finally:
            cur.close()
            conn.close()
    
    return render_template('change_password.html')

@app.route('/view_employee/<int:id>')
@login_required
def view_employee(id):
    """Просмотр сотрудника"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT e.*, d.name as department_name, d.description as department_description,
                   p.name as position_name, p.description as position_description,
                   e.last_name || ' ' || e.first_name || COALESCE(' ' || e.middle_name, '') as full_name,
                   TO_CHAR(e.birth_date, 'DD.MM.YYYY') as birth_date_formatted,
                   TO_CHAR(e.hire_date, 'DD.MM.YYYY') as hire_date_formatted
            FROM employees e
            JOIN departments d ON e.department_id = d.id
            JOIN positions p ON e.position_id = p.id
            WHERE e.id = %s
        """, (id,))
        employee = cur.fetchone()
        
        if not employee:
            flash('Сотрудник не найден', 'error')
            return redirect(url_for('employees'))
        
        return render_template('view_employee.html',
                             employee=employee,
                             is_admin=session.get('is_admin', False))
    finally:
        cur.close()
        conn.close()

def init_database():
    """Инициализация базы данных (создание таблиц и начальных данных)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        with open('init_db.sql', 'r') as f:
            sql_script = f.read()
            cur.execute(sql_script)
            
            admin_password = generate_password_hash('admin123')
            user_password = generate_password_hash('user123')
            
            cur.execute("""
                INSERT INTO users (username, email, password_hash, is_admin) 
                VALUES 
                    ('admin', 'admin@example.com', %s, TRUE),
                    ('user', 'user@example.com', %s, FALSE)
                ON CONFLICT (username) DO NOTHING
            """, (admin_password, user_password))
            
            conn.commit()
            print("База данных успешно инициализирована!")
            print("Тестовые пользователи созданы с хешированными паролями")
    except Exception as e:
        print(f"Ошибка при инициализации БД: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)