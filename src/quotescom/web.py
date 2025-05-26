# -*- coding: utf-8 -*- 
"""
Простое Flask-приложение для добавления, просмотра и удаления цитат
с базовой аутентификацией пользователей.
"""

from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
import sqlite3
import os
from datetime import date


# --- Константы ---
DATA_DIR_IN_CONTAINER = os.environ.get('APP_DATA_DIR', '/app_data') # /data - путь внутри контейнера
DATABASE_FILENAME = 'my_database.db'
DATABASE_PATH = os.path.join(DATA_DIR_IN_CONTAINER, DATABASE_FILENAME)
if not os.path.exists(DATA_DIR_IN_CONTAINER):
    try:
        os.makedirs(DATA_DIR_IN_CONTAINER, exist_ok=True) # exist_ok=True - не будет ошибки, если уже есть
        print(f"Создана или проверена директория для данных: {DATA_DIR_IN_CONTAINER}")
    except OSError as e:
        print(f"Ошибка создания директории {DATA_DIR_IN_CONTAINER}: {e}")
        # Можно решить, что делать дальше - падать или пытаться работать без БД # Путь к файлу БД SQLite
# Рекомендуется использовать относительный путь или переменную окружения для большей гибкости:
# BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# DATABASE_PATH = os.path.join(BASE_DIR, 'data.db')

# --- Инициализация Flask ---
app = Flask(__name__)
# Секретный ключ КРАЙНЕ ВАЖЕН для сессий и защиты форм CSRF
# Лучше генерировать его случайно и хранить безопасно (например, в переменных окружения)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'замени-меня-на-случайный-ключ-в-продакшене')

# --- Настройка Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Имя функции (маршрута) для страницы входа
login_manager.login_message = "Пожалуйста, войдите, чтобы получить доступ к этой странице."
login_manager.login_message_category = "info" # Категория для flash-сообщений

# --- Модели данных ---

class User(UserMixin):
    """
    Класс пользователя для Flask-Login.

    :param id: Уникальный идентификатор пользователя (int).
    :param username: Имя пользователя (str).
    """
    def __init__(self, id, username):
        self.id = id
        self.username = username

# --- Функции для работы с БД ---

def get_db_connection():
    """Устанавливает соединение с базой данных SQLite."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Возвращать строки как объекты, доступные по имени колонки
    return conn

def create_table():
    """
    Создает таблицы 'users' и 'data' в базе данных, если они еще не существуют.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote TEXT NOT NULL,
                author TEXT NOT NULL,
                dateOfadd TEXT,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()
        print("Таблицы успешно проверены/созданы.")
    except sqlite3.Error as e:
        print(f"Ошибка при создании таблиц: {e}")
    finally:
        conn.close()

def delete_data_by_id(quote_id):
    """
    Удаляет цитату из таблицы 'data' по её ID.

    :param quote_id: ID цитаты для удаления (int).
    :return: True, если цитата была удалена, False в противном случае.
    :rtype: bool
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    deleted = False
    try:
        cursor.execute("DELETE FROM data WHERE id=?", (quote_id,))
        conn.commit()
        deleted = cursor.rowcount > 0 # rowcount показывает кол-во измененных строк
    except sqlite3.Error as e:
        print(f"Ошибка при удалении цитаты с ID {quote_id}: {e}")
        conn.rollback() # Откатить изменения в случае ошибки
    finally:
        conn.close()
    return deleted

def retrieve_data():
    """
    Извлекает все цитаты из базы данных вместе с именем добавившего пользователя.

    :return: Список объектов sqlite3.Row, представляющих цитаты,
             или пустой список в случае ошибки.
    :rtype: list
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = []
    try:
        cursor.execute("""
            SELECT d.id, d.quote, d.author, d.dateOfadd, COALESCE(u.username, 'Аноним') as added_by
            FROM data d
            LEFT JOIN users u ON d.user_id = u.id
            ORDER BY d.id DESC
        """)
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка при извлечении данных: {e}")
    finally:
        conn.close()
    return rows

def count_rows():
    """
    Подсчитывает общее количество цитат в таблице 'data'.

    :return: Количество цитат (int) или 0 в случае ошибки.
    :rtype: int
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    count = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM data")
        result = cursor.fetchone()
        if result:
            count = result[0]
    except sqlite3.Error as e:
        print(f"Ошибка при подсчете строк: {e}")
    finally:
        conn.close()
    return count

# --- Flask-Login Callbacks ---

@login_manager.user_loader
def load_user(user_id):
    """
    Загружает пользователя по ID. Требуется для Flask-Login.

    :param user_id: ID пользователя для загрузки (str из сессии).
    :return: Объект User или None, если пользователь не найден.
    :rtype: User or None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    user = None
    try:
        cursor.execute("SELECT id, username FROM users WHERE id = ?", (int(user_id),))
        user_data = cursor.fetchone()
        if user_data:
            user = User(id=user_data['id'], username=user_data['username'])
    except (sqlite3.Error, ValueError) as e:
        print(f"Ошибка при загрузке пользователя {user_id}: {e}")
    finally:
        conn.close()
    return user

# --- Формы Flask-WTF ---

class RegistrationForm(FlaskForm):
    """Форма для регистрации нового пользователя."""
    username = StringField('Логин', validators=[DataRequired("Поле 'Логин' обязательно."),
                                                Length(min=4, max=20, message="Логин должен быть от 4 до 20 символов.")])
    password = PasswordField('Пароль', validators=[DataRequired("Поле 'Пароль' обязательно."),
                                                  Length(min=6, message="Пароль должен быть не менее 6 символов.")])
    confirm_password = PasswordField('Повторите пароль',
                                     validators=[DataRequired("Повторите пароль."),
                                                 EqualTo('password', message="Пароли должны совпадать.")])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        """Проверяет, не занято ли имя пользователя."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username.data,))
            user = cursor.fetchone()
            if user:
                raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')
        except sqlite3.Error as e:
            print(f"Ошибка при валидации имени пользователя {username.data}: {e}")
            # Возможно, стоит генерировать ValidationError и здесь, чтобы не пропускать регистрацию
            raise ValidationError('Ошибка при проверке имени пользователя. Попробуйте позже.')
        finally:
            conn.close()

class LoginForm(FlaskForm):
    """Форма для входа пользователя."""
    username = StringField('Логин', validators=[DataRequired("Введите логин.")])
    password = PasswordField('Пароль', validators=[DataRequired("Введите пароль.")])
    submit = SubmitField('Войти')

# --- Маршруты Flask ---

@app.route('/')
def index():
    """
    Главная страница. Отображает список цитат и форму для добавления.
    """
    quotes_data = retrieve_data()
    return render_template('delete.html', data=quotes_data) # Используем основной шаблон

@app.route('/add_quote', methods=['POST'])
def add_quote():
    """
    Обрабатывает добавление новой цитаты через POST-запрос (AJAX).
    Требует аутентификации пользователя.

    :form quote: Текст цитаты.
    :form author: Автор цитаты.
    :return: JSON с сообщением об успехе или ошибке.
    :rtype: Response
    """
    # Проверка метода уже не нужна, т.к. указано methods=['POST']
    quote = request.form.get('quote')
    author = request.form.get('author')

    if not quote or not author:
        return jsonify({'error': 'Необходимо указать цитату и автора'}), 400

    user_id = None # По умолчанию считаем пользователя анонимным
    if current_user.is_authenticated: # ПРОВЕРЯЕМ АУТЕНТИФИКАЦИЮ СНАЧАЛА
        user_id = current_user.id # Получаем ID вошедшего пользователя
    conn = get_db_connection()
    cursor = conn.cursor()
    today = date.today().strftime('%Y-%m-%d')

    try:
        cursor.execute("INSERT INTO data (quote, author, dateOfadd, user_id) VALUES (?, ?, ?, ?)",
                      (quote, author, today, user_id))
        conn.commit()
        # flash('Цитата добавлена!', 'success') # Можно использовать для не-AJAX
        return jsonify({'message': 'Цитата успешно добавлена'})
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Ошибка при добавлении цитаты: {e}")
        return jsonify({'error': 'Ошибка при сохранении цитаты в базу данных'}), 500
    finally:
        conn.close()


@app.route('/delete_quote', methods=['POST'])
@login_required # Пример: только залогиненные могут удалять
def delete_quote():
    """
    Обрабатывает удаление цитаты через POST-запрос (AJAX).
    Требует аутентификации.

    :form quote_id: ID цитаты для удаления.
    :return: JSON с сообщением об успехе или ошибке.
    :rtype: Response
    """
    quote_id = request.form.get('quote_id')
    if not quote_id:
        return jsonify({'error': 'Необходимо указать ID цитаты для удаления'}), 400

    try:
        quote_id_int = int(quote_id)
        # --- Дополнительная проверка: может ли текущий пользователь удалить эту цитату? ---
        # conn = get_db_connection()
        # cursor = conn.cursor()
        # cursor.execute("SELECT user_id FROM data WHERE id = ?", (quote_id_int,))
        # quote_data = cursor.fetchone()
        # conn.close()
        # if not quote_data:
        #     return jsonify({'error': 'Цитата не найдена'}), 404
        # # Разрешаем удалять только свои цитаты (или можно добавить роль админа)
        # if quote_data['user_id'] != current_user.id:
        #      return jsonify({'error': 'Вы не можете удалить эту цитату'}), 403
        # --- Конец проверки ---

        if delete_data_by_id(quote_id_int):
            return jsonify({'message': 'Цитата успешно удалена'})
        else:
            return jsonify({'error': 'Цитата с таким ID не найдена или уже удалена'}), 404
    except ValueError:
        return jsonify({'error': 'Некорректный ID цитаты'}), 400
    except Exception as e: # Ловим другие возможные ошибки (например, при проверке прав)
        print(f"Непредвиденная ошибка при удалении цитаты {quote_id}: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера при удалении'}), 500


# Маршрут /retrieve, вероятно, не нужен, если все данные грузятся AJAX'ом через /get_quotes
# @app.route('/retrieve')
# def retrieve():
#     """Отображает страницу со всеми цитатами (если нужна отдельная)."""
#     data = retrieve_data()
#     # Нужен шаблон retrieve.html
#     return render_template('retrieve.html', data=data)

@app.route('/get_quotes')
def get_quotes():
    """
    Возвращает список всех цитат в формате JSON для использования в AJAX-запросах.
    """
    quotes_data = retrieve_data() # Функция уже возвращает Row объекты
    quotes_list = []
    for row in quotes_data:
        # Преобразуем Row объект в словарь
        quotes_list.append(dict(row)) # dict(row) удобно преобразует Row в словарь
    return jsonify({'quotes': quotes_list})


@app.route('/row_count')
def row_count_route(): # Изменил имя, чтобы не конфликтовать с функцией
    """Возвращает общее количество цитат в формате JSON."""
    count = count_rows()
    return jsonify({'row_count': count})

@app.route('/status')
def check_status():
    """Простой маршрут для проверки, что приложение запущено."""
    return jsonify({'status': 'running', 'message': 'Quote app is alive!'})

# --- Маршруты аутентификации ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Отображает и обрабатывает форму регистрации."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Имя пользователя уже проверено методом validate_username формы
        hashed_password = generate_password_hash(form.password.data)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                          (form.username.data, hashed_password))
            conn.commit()
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            # Эта ошибка не должна возникать из-за validate_username, но на всякий случай
            conn.rollback()
            flash('Это имя пользователя уже занято.', 'danger')
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Ошибка БД при регистрации пользователя {form.username.data}: {e}")
            flash('Произошла ошибка при регистрации. Попробуйте позже.', 'danger')
        finally:
            conn.close()
    # Если GET запрос или форма не прошла валидацию
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Отображает и обрабатывает форму входа."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        user = None
        try:
            cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (form.username.data,))
            user_data = cursor.fetchone()
            if user_data and check_password_hash(user_data['password_hash'], form.password.data):
                user = User(id=user_data['id'], username=user_data['username'])
            else:
                flash('Неверный логин или пароль.', 'danger')
        except sqlite3.Error as e:
            print(f"Ошибка БД при входе пользователя {form.username.data}: {e}")
            flash('Произошла ошибка при входе. Попробуйте позже.', 'danger')
        finally:
            conn.close()

        if user:
            login_user(user) # Функция Flask-Login для сохранения пользователя в сессии
            flash('Вход выполнен успешно!', 'success')
            next_page = request.args.get('next')
            # Проверка безопасности: убедиться, что next_page - это внутренний URL
            # (пропущено для простоты, но важно в реальных приложениях)
            return redirect(next_page or url_for('index'))
        # Если user is None (неверный пароль или ошибка БД) - рендерим форму снова
    return render_template('login.html', title='Вход', form=form)

@app.route('/logout')
@login_required # Выйти может только тот, кто вошел
def logout():
    """Выполняет выход пользователя из системы."""
    logout_user() # Функция Flask-Login для очистки сессии
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

# --- Точка входа ---
if __name__ == '__main__':
    print("Инициализация приложения...")
    create_table() # Убедимся, что таблицы существуют перед запуском
    print(f"Запуск Flask development server на http://0.0.0.0:8080")
    # Используем debug=True только для разработки!
    # host='0.0.0.0' делает сервер доступным в локальной сети
    app.run(debug=True, host='0.0.0.0', port=8080)