from flask import Flask, jsonify, request, render_template
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
import sqlite3
import os
from datetime import date
from flask import redirect, url_for, flash
DATABASE_PATH = 'C:\\mydatabase\\data.db'

def add_columns():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE data ADD COLUMN quote TEXT")
        cursor.execute("ALTER TABLE data ADD COLUMN author TEXT")
        cursor.execute("ALTER TABLE data ADD COLUMN dateOfadd TEXT")
        conn.commit()
        print("Столбцы 'quote', 'author' и 'dateOfadd' успешно добавлены.")
    except sqlite3.OperationalError as e:
        print(f"Ошибка при добавлении столбцов: {e}")
    finally:
        conn.close()
app = Flask(__name__)


def create_table():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS data (
                id INTEGER PRIMARY KEY AUTOINCREMENT, -- Хорошо бы добавить ID для цитат
                quote TEXT NOT NULL,
                author TEXT NOT NULL,
                dateOfadd TEXT,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')
    conn.commit()
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )''')
    conn.commit()
    conn.close()



def delete_data_by_id(quote_id): # Новое имя и параметр
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    # Возможно, добавить проверку, что цитату удаляет ее автор или админ? (Пока не делаем)
    c.execute("DELETE FROM data WHERE id=?", (quote_id,)) # Удаляем по ID
    conn.commit()
    # Проверить, была ли строка удалена (опционально)
    deleted_rows = c.rowcount
    conn.close()
    return deleted_rows > 0 # Возвращать True если удалено, False если нет

def retrieve_data():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Удобно для доступа по имени колонки
    c = conn.cursor()
    c.execute("""
        SELECT d.id, d.quote, d.author, d.dateOfadd, COALESCE(u.username, 'Аноним') as added_by
        FROM data d
        LEFT JOIN users u ON d.user_id = u.id
        ORDER BY d.id DESC
    """)
    rows = c.fetchall()
    conn.close()
    # rows будет списком объектов Row, доступ к данным по индексу или имени колонки
    # Например: rows[0]['id'], rows[0]['quote'], rows[0]['added_by']
    return rows


@app.route('/')
def index():
    data = retrieve_data()
    return render_template('delete.html', data=data)

def count_rows():
    conn = sqlite3.connect('C:\\mydatabase\\data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM data")
    row_count = c.fetchone()[0]
    conn.close()
    return row_count



@app.route('/add_quote', methods=["POST"])
def add_quote():
    if request.method == 'POST':
        quote = request.form.get('quote')
        author = request.form.get('author')
        if quote and author:
            user_id = current_user.id if current_user.is_authenticated else None # Получаем ID вошедшего юзера или None
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            today = date.today().strftime('%Y-%m-%d')
            # Вставляем user_id
            c.execute("INSERT INTO data (quote, author, dateOfadd, user_id) VALUES (?, ?, ?, ?)",
                      (quote, author, today, user_id))
            conn.commit()
            conn.close()
            # flash('Цитата добавлена!', 'success') # Можно добавить flash-сообщение
            return jsonify({'message': 'Цитата успешно добавлена'})
        return jsonify({'error': 'Необходимо указать цитату и автора'}), 400
    return jsonify({'error': 'Неверный метод запроса'}), 405

@app.route('/delete_quote', methods=["POST"])
# @login_required # Возможно, удалять могут только залогиненные?
def delete_quote():
    if request.method == 'POST':
        quote_id = request.form.get('quote_id') # Ожидаем ID из формы
        if quote_id:
            try:
                # Преобразуем ID в целое число
                quote_id_int = int(quote_id)
                if delete_data_by_id(quote_id_int): # Вызываем новую функцию
                    return jsonify({'message': 'Цитата успешно удалена'})
                else:
                    # Если delete_data_by_id вернула False (ID не найден)
                    return jsonify({'error': 'Цитата с таким ID не найдена'}), 404
            except ValueError:
                return jsonify({'error': 'Некорректный ID цитаты'}), 400
        return jsonify({'error': 'Необходимо указать ID цитаты для удаления'}), 400
    return jsonify({'error': 'Неверный метод запроса'}), 405


@app.route('/retrieve')
def retrieve():
    data = retrieve_data()
    return render_template('retrieve.html', data=data)

@app.route('/row_count')
def row_count():
    count = count_rows()
    return jsonify({'row_count': count})

@app.route('/get_quotes')
def get_quotes():
    data = retrieve_data() # Теперь возвращает объекты Row с id и added_by
    quotes_list = []
    for row in data:
        # Добавляем все нужные поля в словарь
        quotes_list.append({
            'id': row['id'], # ID цитаты
            'quote': row['quote'],
            'author': row['author'],
            'dateOfadd': row['dateOfadd'],
            'added_by': row['added_by'] # Кем добавлено
         })
    return jsonify({'quotes': quotes_list})

@app.route('/status')
def check_status():
    return jsonify({'status': 'running'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: # Если уже вошел, перенаправить
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                      (form.username.data, hashed_password))
            conn.commit()
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError: # Если имя уже занято (хотя validate_username должна была поймать)
             flash('Ошибка регистрации.', 'danger')
        finally:
            conn.close()
    return render_template('register.html', title='Регистрация', form=form) # Нужен шаблон register.html

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (form.username.data,))
        user_data = c.fetchone()
        conn.close()
        if user_data and check_password_hash(user_data[2], form.password.data):
            user = User(id=user_data[0], username=user_data[1])
            login_user(user) # Функция Flask-Login для входа пользователя
            flash('Вход выполнен успешно!', 'success')
            # Перенаправить на страницу, куда пользователь пытался попасть, или на главную
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль.', 'danger')
    return render_template('login.html', title='Вход', form=form) # Нужен шаблон login.html

@app.route('/logout')
def logout():
    logout_user() # Функция Flask-Login для выхода
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

app.config['SECRET_KEY'] = 'kdjf2309dlfj190' # ОБЯЗАТЕЛЬНО установи секретный ключ

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Куда перенаправлять, если юзер не вошел, но пытается зайти на защищенную страницу

# Модель пользователя для Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Функция для загрузки пользователя из сессии
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE id = ?", (int(user_id),))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data[0], username=user_data[1])
    return None

# Формы для регистрации и входа (с помощью Flask-WTF)
class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    # Проверка, что имя пользователя еще не занято
    def validate_username(self, username):
         conn = sqlite3.connect(DATABASE_PATH)
         c = conn.cursor()
         c.execute("SELECT id FROM users WHERE username = ?", (username.data,))
         user = c.fetchone()
         conn.close()
         if user:
             raise ValidationError('Это имя пользователя уже занято.')

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

if __name__ == '__main__':
    create_table()  
    app.run(debug=True, host='0.0.0.0', port=8080)

