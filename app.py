import os
from flask import Flask, render_template, request, redirect, url_for
import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename
import sqlite3
import time

db_name = 'database.db'

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def create_table(objects, filename):
    count = 0
    tables = get_existing_tables()
    for table in tables:
        if table == filename:
            count += 1
    if count == 0:
        connect = sqlite3.connect(db_name)
        cursor = connect.cursor()
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {filename}(
                          id TEXT PRIMARY KEY,
                          value TEXT,
                          source TEXT,
                          target TEXT,
                          description TEXT, 
                          type TEXT)''')

        connect.commit()

        for obj in objects:
            if obj['source'] is not None and obj['target'] is not None and len(obj['id']) > 2:
                cursor.execute(
                    f"INSERT INTO {filename} (id, value, source, target, description, type) VALUES (?, ?, ?, ?, ?, ?)",
                    (obj['id'], obj['value'], obj['source'], obj['target'], '', 'relationship'))
            elif obj['source'] is None and obj['target'] is None and len(obj['id']) > 2:
                cursor.execute(
                    f"INSERT INTO {filename} (id, value, source, target, description, type) VALUES (?, ?, ?, ?, ?, ?)",
                    (obj['id'], obj['value'], obj['source'], obj['target'], '', 'object'))
        connect.commit()
    else:
        print('')


def delete_table(filename):
    connect = sqlite3.connect(db_name)
    cursor = connect.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {filename}")
    connect.commit()


def get_existing_tables():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    return [table[0] for table in tables]


def get_table_data(table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    data = cursor.fetchall()
    conn.close()
    return data


def parse_xml(file_contents):
    root = ET.fromstring(file_contents)
    objects = []
    for obj in root.findall('.//mxCell'):
        obj_data = {}
        obj_data['id'] = obj.get('id')
        obj_data['value'] = obj.get('value')
        obj_data['source'] = obj.get('source')
        obj_data['target'] = obj.get('target')
        objects.append(obj_data)

    return objects


@app.route('/', methods=['GET', 'POST'])
def home_page():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)
            file_contents = uploaded_file.read().decode('utf-8')
            objects = parse_xml(file_contents)
            full_filename = str(time.time_ns()) + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(file_path)
            str_filename = filename.split('.')[0]
            create_table(objects, filename=str_filename)

            return redirect(url_for('database_page'))
    return render_template('home.html')


@app.route('/database')
def database_page():
    tables = get_existing_tables()
    return render_template('database.html', tables=tables)


@app.route('/delete_database/<filename>')
def delete_database(filename):
    file_path = f'uploads/{filename}.xml'
    if os.path.exists(file_path):
        os.remove(file_path)
    delete_table(filename)
    return redirect('/database')


@app.route('/deldata')
def del_data():
    file_path = 'database.db'
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Файл {file_path} успешно удален.")
    else:
        print(f"Файл {file_path} не существует.")
    return redirect('/')


@app.route('/diagram_page/<table_name>')
def diagram_page(table_name):
    diagramm = []
    table_data = get_table_data(table_name)
    for i in range(0, len(table_data)):
        rel = []
        start_point = ''
        end_point = ''
        val = ''
        if table_data[i][-1] == 'relationship':
            start_point = table_data[i][2]
            end_point = table_data[i][3]
            val = table_data[i][1]

            for j in range(0, len(table_data)):
                if table_data[j][0] == start_point:
                    rel.append(table_data[j][1])
            rel.append(val)
            for j in range(0, len(table_data)):
                if table_data[j][0] == end_point:
                    rel.append(table_data[j][1])

            diagramm.append(rel)

    return render_template('diagram_page.html', table_name=table_name, table_data=table_data, diagramm=diagramm)


@app.route('/data/<table_name>')
def data_page(table_name):
    table_data = get_table_data(table_name)
    return render_template('data_page.html', table_name=table_name, table_data=table_data)


@app.route('/term/<table_name>')
def term(table_name):
    terms = []
    table_data = get_table_data(table_name)
    for i in range(0, len(table_data)):
        term = []
        if table_data[i][1] is not None:
            term.append(table_data[i][1])
            term.append(table_data[i][4])
        if term != []:
            terms.append(term)

    return render_template('term_page.html', table_name=table_name, table_data=table_data, terms=terms)


@app.route('/edit/<table_name>', methods=['GET'])
def edit_values(table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    table_data = cursor.fetchall()
    conn.close()
    return render_template('edit_diagram.html', table_data=table_data, table_name=table_name)


@app.route('/update_values/<table_name>', methods=['POST'])
def update_values(table_name):
    for key, value in request.form.items():
        if key.startswith('value_'):
            row_id = key.split('_')[1]
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {table_name} SET value=? WHERE id=?", (value, row_id))
            conn.commit()
            conn.close()
    return redirect(url_for('diagram_page', table_name=table_name))


@app.route('/edit_term/<table_name>', methods=['GET'])
def edit_term(table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    table_data = cursor.fetchall()
    conn.close()
    return render_template('edit_term.html', table_data=table_data, table_name=table_name)


@app.route('/update_description/<table_name>', methods=['POST'])
def update_description(table_name):
    for key, value in request.form.items():
        if key.startswith('value_'):
            row_id = key.split('_')[1]
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {table_name} SET description=? WHERE id=?", (value, row_id))
            conn.commit()
            conn.close()
    return redirect(url_for('term', table_name=table_name))


if __name__ == '__main__':
    app.run(debug=True, port=8000)
