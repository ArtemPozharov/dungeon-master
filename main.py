import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from flask_ckeditor import CKEditor
from markupsafe import Markup

app = Flask(__name__)
ckeditor = CKEditor(app)


def initialize_database():
    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()

    # Создание таблицы "categories"
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL)''')

    # Создание таблицы "knowledge_objects"
    cursor.execute('''CREATE TABLE IF NOT EXISTS knowledge_objects
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       category_id INTEGER NOT NULL,
                       name TEXT NOT NULL,
                       text TEXT NOT NULL,
                       FOREIGN KEY (category_id) REFERENCES categories (id))''')

    # Проверка наличия начальных категорий
    cursor.execute("SELECT COUNT(*) FROM categories")
    count = cursor.fetchone()[0]
    if count == 0:
        # Добавление начальных категорий
        categories = [
            ('Юридические вопросы',),
            ('Питание',),
            ('Недвижимость',),
            ('Реклама',),
            ('Маркетинг',)
        ]
        cursor.executemany("INSERT INTO categories (name) VALUES (?)", categories)

    conn.commit()
    conn.close()


def update_search_data():
    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_objects")
    objects = cursor.fetchall()
    conn.close()

    # Обновление данных для поиска
    search_data = []
    for obj in objects:
        obj_id = obj[0]
        category_id = obj[1]
        name = obj[2]
        text = obj[3]

        # Добавление объекта знания в данные для поиска
        search_data.append({
            'id': obj_id,
            'category_id': category_id,
            'name': name,
            'text': text
        })

    # Здесь можно сохранить данные для поиска в нужном формате или базе данных


def update_catalog_data():
    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()

    # Получение списка категорий знаний
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    # Получение списка объектов знаний
    cursor.execute("SELECT * FROM knowledge_objects")
    objects = cursor.fetchall()

    conn.close()

    # Обновление данных для каталога знаний
    catalog_data = []
    for category in categories:
        category_id = category[0]
        category_name = category[1]

        category_objects = []
        for obj in objects:
            obj_id = obj[0]
            obj_category_id = obj[1]
            obj_name = obj[2]
            obj_text = obj[3]

            if obj_category_id == category_id:
                category_objects.append({
                    'id': obj_id,
                    'name': obj_name,
                    'text': obj_text
                })

        catalog_data.append({
            'id': category_id,
            'name': category_name,
            'objects': category_objects
        })

    # Здесь можно сохранить данные для каталога знаний в нужном формате или базе данных


@app.template_filter('highlight')
def highlight_filter(s, search_word):
    pattern = re.compile(re.escape(search_word), re.IGNORECASE)
    highlighted = pattern.sub(f'<span class="highlight">{search_word}</span>', s)
    return Markup(highlighted)


@app.route('/')
def catalog():
    update_catalog_data()

    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cursor.execute("SELECT * FROM knowledge_objects")
    objects = cursor.fetchall()

    conn.close()

    search_word = request.args.get('search', '')

    if search_word:
        search_results = []
        for category in categories:
            category_id = category[0]
            category_name = category[1]

            category_objects = []
            for obj in objects:
                obj_id = obj[0]
                obj_category_id = obj[1]
                obj_name = obj[2]
                obj_text = obj[3]

                if obj_category_id == category_id and search_word.lower() in obj_name.lower():
                    category_objects.append({
                        'id': obj_id,
                        'name': obj_name,
                        'text': obj_text
                    })

            if category_objects:
                search_results.append({
                    'category_name': category_name,
                    'objects': category_objects
                })

        return render_template('catalog.html', categories=categories, objects=objects, search_results=search_results,
                               search_word=search_word)
    else:
        search_results = []
        for category in categories:
            category_id = category[0]
            category_name = category[1]

            category_objects = []
            for obj in objects:
                obj_id = obj[0]
                obj_category_id = obj[1]
                obj_name = obj[2]
                obj_text = obj[3]

                if obj_category_id == category_id:
                    category_objects.append({
                        'id': obj_id,
                        'name': obj_name,
                        'text': obj_text
                    })

            if category_objects:
                search_results.append({
                    'category_name': category_name,
                    'objects': category_objects
                })

        return render_template('catalog.html', categories=categories, objects=objects, search_results=search_results,
                               search_word=search_word)


@app.route('/edit', methods=['GET', 'POST'])
def edit():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        text = request.form['text']
        object_id = request.form['object_id']

        conn = sqlite3.connect('knowledge_base.db')
        cursor = conn.cursor()

        if object_id:
            cursor.execute("UPDATE knowledge_objects SET category_id = ?, name = ?, text = ? WHERE id = ?",
                           (category, name, text, object_id))
        else:
            cursor.execute("INSERT INTO knowledge_objects (category_id, name, text) VALUES (?, ?, ?)",
                           (category, name, text))

        conn.commit()
        conn.close()

        update_search_data()
        update_catalog_data()

        return redirect(url_for('catalog'))

    object_id = request.args.get('id')

    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    if object_id:
        cursor.execute("SELECT * FROM knowledge_objects WHERE id = ?", (object_id,))
        object_data = cursor.fetchone()
    else:
        object_data = None

    conn.close()

    return render_template('edit.html', categories=categories, object_data=object_data)


@app.route('/delete/<int:object_id>', methods=['POST'])
def delete_object(object_id):
    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM knowledge_objects WHERE id = ?", (object_id,))
    conn.commit()
    conn.close()

    update_search_data()
    update_catalog_data()

    return redirect(url_for('catalog'))


if __name__ == '__main__':
    initialize_database()
    app.run()