from flask import Flask, jsonify, request, render_template
import sqlite3
import os
from datetime import date
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
                quote TEXT,
                author TEXT,
                dateOfadd TEXT
            )''')
    conn.commit()
    conn.close()

def insert_data(quote, author):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    today = date.today().strftime('%Y-%m-%d')  # Форматируем дату как 'YYYY-MM-DD'
    c.execute("INSERT INTO data (quote, author, dateOfadd) VALUES (?, ?, ?)", (quote, author, today))
    conn.commit()
    conn.close()

def delete_data(quote):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM data WHERE quote=?", (quote,))
    conn.commit()
    conn.close()

def retrieve_data():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT quote, author, dateOfadd FROM data")
    rows = c.fetchall()
    conn.close()
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
            insert_data(quote, author)
            return jsonify({'message': 'Цитата успешно добавлена'})
        return jsonify({'error': 'Необходимо указать цитату и authorа'}), 400
    return jsonify({'error': 'Неверный метод запроса'}), 405

@app.route('/delete_quote', methods=["POST"])
def delete_quote():
    if request.method == 'POST':
        quote = request.form.get('quote')
        if quote:
            delete_data(quote)
            return jsonify({'message': 'Цитата успешно удалена'})
        return jsonify({'error': 'Необходимо указать цитату для удаления'}), 400
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
    data = retrieve_data()
    quotes_list = ''
    for row in data:
        quotes_list.append({'quote': row, 'author': row[1], 'dateOfadd': row[2]})
    return jsonify({'quotes': quotes_list})


@app.route('/status')
def check_status():
    return jsonify({'status': 'running'})

if __name__ == '__main__':
    create_table()  
    app.run(debug=True, host='0.0.0.0', port=8080)

