from flask import Flask, jsonify, request, render_template
import sqlite3

app = Flask(__name__)


def create_table():
    conn = sqlite3.connect('C:\\mydatabase\\data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS data (key TEXT, value TEXT)''')
    conn.commit()
    conn.close()

def insert_data(key, value):
    conn = sqlite3.connect('C:\\mydatabase\\data.db')
    c = conn.cursor()
    c.execute("INSERT INTO data (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def delete_data(key):
    conn = sqlite3.connect('C:\\mydatabase\\data.db')
    c = conn.cursor()
    c.execute("DELETE FROM data WHERE key=?", (key,))
    conn.commit()
    conn.close()

def retrieve_data():
    conn = sqlite3.connect('C:\\mydatabase\\data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM data")
    rows = c.fetchall()
    conn.close()
    return rows

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



@app.route('/delete', methods=['GET', 'POST'])
def delete():
    data = retrieve_data()
    if request.method == 'POST':
        key = request.form.get('key')
        if key is None:
            return jsonify({'error': 'Key field is missing in the form data'}), 400
        delete_data(key, )
        return jsonify({'message': 'Data deleted successfully'})
    return render_template('delete.html', data=data)

@app.route('/insert', methods=['GET', 'POST'])
def insert():
    if request.method == 'POST':
        key = request.form['key']
        value = request.form['value']
        insert_data(key, value)
        return jsonify({'message': 'Data inserted successfully'})
    return render_template('insert.html')


@app.route('/retrieve')
def retrieve():
    data = retrieve_data()
    return render_template('retrieve.html', data=data)

@app.route('/row_count')
def row_count():
    count = count_rows()
    return jsonify({'row_count': count})

@app.route('/')
def hello_world():
    return 'Моё приложение!'

@app.route('/status')
def check_status():
    return jsonify({'status': 'running'})

if __name__ == '__main__':
    create_table()  
    app.run(debug=True, host='0.0.0.0', port=8080)


#comment!