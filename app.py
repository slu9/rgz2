import os
import sqlite3
import hashlib
import random
from datetime import datetime, timedelta
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)

app = Flask(__name__)
app.secret_key = "change-me"

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "storage.db")

# ------------------ Вспомогательные функции ------------------

def get_student_info():
    return "Зырянова Софья", "ФБИ-34"

def get_db():
    return sqlite3.connect(DB_PATH)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_theme():
    """Получаем текущую тему из формы или сессии"""
    return request.form.get('theme', session.get('theme', 'day'))

# ------------------ Главная страница ------------------

@app.route("/")
def index():
    student_name, student_group = get_student_info()

    # Сохраняем тему
    theme = get_current_theme()
    session['theme'] = theme

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cells.id, cells.user_id, cells.building_type, users.name
        FROM cells
        LEFT JOIN users ON users.id = cells.user_id
        ORDER BY cells.id;
    """)
    rows = cursor.fetchall()
    
    # Получаем баланс текущего пользователя
    user_balance = 0
    if session.get("user_id"):
        cursor.execute("SELECT balance FROM users WHERE id = ?;", (session["user_id"],))
        balance_row = cursor.fetchone()
        if balance_row:
            user_balance = balance_row[0]
    
    conn.close()

    cells = []
    for cell_id, user_id, building_type, owner_name in rows:
        cells.append({
            "id": cell_id,
            "occupied": user_id is not None,
            "building_type": building_type,
            "owner_name": owner_name
        })

    return render_template(
        "index.html",
        cells=cells,
        rows=10,
        cols=10,
        student_name=student_name,
        student_group=student_group,
        current_user=session.get("name"),
        user_balance=user_balance
    )

# ------------------ Регистрация ------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    student_name, student_group = get_student_info()

    if request.method == "POST":
        name = request.form.get("name")
        login = request.form.get("login")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")

        if not name or not login or not password:
            flash("Заполните все поля.")
            return redirect(url_for("register"))

        if password != password_confirm:
            flash("Пароли не совпадают.")
            return redirect(url_for("register"))

        password_hash = hash_password(password)

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name, login, password_hash, balance) VALUES (?, ?, ?, 1000);",
                (name, login, password_hash)
            )
            conn.commit()
            flash("Регистрация успешна! На ваш счет начислено 1000 рублей. Теперь войдите.")
        except sqlite3.IntegrityError:
            flash("Такой логин уже существует.")
            conn.rollback()
        finally:
            conn.close()

        return redirect(url_for("login"))

    # Сохраняем тему
    theme = get_current_theme()
    session['theme'] = theme

    return render_template(
        "register.html",
        student_name=student_name,
        student_group=student_group,
        current_user=session.get("name")
    )

# ------------------ Вход ------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    student_name, student_group = get_student_info()

    if request.method == "POST":
        login_val = request.form.get("login")
        password = request.form.get("password")
        password_hash = hash_password(password)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, balance FROM users WHERE login = ? AND password_hash = ?;",
            (login_val, password_hash)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["name"] = user[1]
            session["balance"] = user[2]
            
            # Сохраняем тему
            theme = get_current_theme()
            session['theme'] = theme
            
            flash("Вы успешно вошли.")
            return redirect(url_for("index"))
        else:
            flash("Неверный логин или пароль.")
            return redirect(url_for("login"))

    # Сохраняем тему
    theme = get_current_theme()
    session['theme'] = theme

    return render_template(
        "login.html",
        student_name=student_name,
        student_group=student_group,
        current_user=session.get("name")
    )

# ------------------ Выход ------------------

@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из аккаунта.")
    return redirect(url_for("index"))

# ------------------ Бронирование ячейки ------------------

@app.route("/cell/<int:cell_id>/build/<int:building_type>", methods=["POST"])
def build_cell(cell_id, building_type):
    user_id = session.get("user_id")
    if not user_id:
        flash("Сначала войдите в аккаунт.")
        return redirect(url_for("login"))

    # Сохраняем тему
    theme = get_current_theme()
    session['theme'] = theme

    conn = get_db()
    cursor = conn.cursor()

    # Проверяем баланс пользователя
    cursor.execute("SELECT balance FROM users WHERE id = ?;", (user_id,))
    user_balance = cursor.fetchone()[0]

    # Стоимость аренды в зависимости от типа здания
    rental_prices = {1: 100, 2: 150, 3: 200, 4: 120, 5: 180}
    price = rental_prices.get(building_type, 100)

    if user_balance < price:
        conn.close()
        flash(f"Недостаточно средств. Стоимость аренды: {price} руб. Ваш баланс: {user_balance} руб.")
        return redirect(url_for("index"))

    # проверяем, свободна ли ячейка
    cursor.execute("SELECT user_id FROM cells WHERE id = ?", (cell_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash("Такой ячейки нет.")
        return redirect(url_for("index"))

    owner = row[0]
    if owner is not None:
        conn.close()
        flash("Эта ячейка уже занята!")
        return redirect(url_for("index"))

    # считаем сколько уже занято
    cursor.execute("SELECT COUNT(*) FROM cells WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]

    if count >= 5:
        conn.close()
        flash("Нельзя занять больше 5 ячеек.")
        return redirect(url_for("index"))

    # Списываем деньги и бронируем ячейку
    cursor.execute(
        "UPDATE users SET balance = balance - ? WHERE id = ?;",
        (price, user_id)
    )
    
    cursor.execute(
        "UPDATE cells SET user_id = ?, building_type = ? WHERE id = ?;",
        (user_id, building_type, cell_id)
    )
    
    # Обновляем баланс в сессии
    session["balance"] = user_balance - price
    
    conn.commit()
    conn.close()

    flash(f"Ячейка успешно арендована за {price} руб! На балансе осталось: {user_balance - price} руб.")
    # передаём номер ячейки, чтобы на фронте её подсветить и проскроллить
    return redirect(url_for("index", new_building=cell_id))

# ------------------ Освобождение ячейки ------------------

@app.route("/cell/<int:cell_id>/toggle", methods=["POST"])
def toggle_cell(cell_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Авторизуйтесь, чтобы управлять ячейками.")
        return redirect(url_for("login"))

    # Сохраняем тему
    theme = request.form.get('theme', session.get('theme', 'day'))
    session['theme'] = theme

    # понять, откуда пришёл запрос (профиль или карта)
    from_profile = request.form.get("from_profile") == "1"

    conn = get_db()
    cursor = conn.cursor()

    # узнаём владельца ячейки
    cursor.execute("SELECT user_id FROM cells WHERE id = ?;", (cell_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        flash("Такой ячейки не существует.")
        return redirect(url_for("index"))

    current_owner = row[0]

    # ---------- Своя ячейка → освободить ----------
    if current_owner == user_id:
        cursor.execute(
            "UPDATE cells SET user_id = NULL, building_type = NULL WHERE id = ?;",
            (cell_id,)
        )
        conn.commit()
        conn.close()
        flash(f"Ячейка {cell_id} освобождена.")

        # если освобождали из профиля — остаёмся в профиле
        if from_profile:
            return redirect(url_for("profile"))
        # если кликали на карте — возвращаемся на карту и скроллим к ячейке
        return redirect(url_for("index", removed_cell=cell_id))

    # ---------- Чужая ячейка ----------
    cursor.execute("""
        SELECT users.name
        FROM cells
        JOIN users ON users.id = cells.user_id
        WHERE cells.id = ?;
    """, (cell_id,))
    owner_row = cursor.fetchone()
    conn.close()

    owner_name = owner_row[0] if owner_row else "другим пользователем"
    flash(f"Эта ячейка уже арендована пользователем: {owner_name}.")
    return redirect(url_for("index"))

# ------------------ Пополнение баланса ------------------

@app.route("/topup", methods=["POST"])
def topup_balance():
    user_id = session.get("user_id")
    if not user_id:
        flash("Сначала войдите в аккаунт.")
        return redirect(url_for("login"))

    # Сохраняем тему
    theme = get_current_theme()
    session['theme'] = theme

    amount = 1000  # Фиксированное пополнение на 1000 рублей

    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?;",
        (amount, user_id)
    )
    
    # Обновляем баланс в сессии
    cursor.execute("SELECT balance FROM users WHERE id = ?;", (user_id,))
    new_balance = cursor.fetchone()[0]
    session["balance"] = new_balance
    
    conn.commit()
    conn.close()

    flash(f"Баланс успешно пополнен на {amount} руб! Текущий баланс: {new_balance} руб.")
    return redirect(url_for("profile"))

# ------------------ Личный кабинет ------------------

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        flash("Сначала войдите в аккаунт.")
        return redirect(url_for("login"))

    student_name, student_group = get_student_info()

    # Сохраняем тему
    theme = get_current_theme()
    session['theme'] = theme

    conn = get_db()
    cursor = conn.cursor()

    # Получаем данные пользователя
    cursor.execute("""
        SELECT name, login, balance 
        FROM users 
        WHERE id = ?;
    """, (session["user_id"],))
    user_data = cursor.fetchone()

    # Получаем арендованные ячейки пользователя
    cursor.execute("""
        SELECT id, building_type 
        FROM cells 
        WHERE user_id = ? 
        ORDER BY id;
    """, (session["user_id"],))
    user_cells = cursor.fetchall()

    conn.close()

    building_names = {
        1: "🏪 Магазин", 
        2: "🏥 Больница", 
        3: "🏛️ Музей", 
        4: "📮 Почта", 
        5: "🏨 Отель"
    }

    cells_with_names = []
    for cell_id, building_type in user_cells:
        cells_with_names.append({
            "id": cell_id,
            "building_name": building_names.get(building_type, "Неизвестно")
        })

    return render_template(
        "profile.html",
        user_name=user_data[0],
        user_login=user_data[1],
        user_balance=user_data[2],
        user_cells=cells_with_names,
        student_name=student_name,
        student_group=student_group,
        current_user=session.get("name"),
        user_balance_display=user_data[2]
    )

# ------------------ Тарифы и правила ------------------

@app.route("/pricing")
def pricing():
    student_name, student_group = get_student_info()

    # Сохраняем тему
    theme = get_current_theme()
    session['theme'] = theme

    rental_prices = {
        1: {"name": "🏪 Магазин", "price": 100, "description": "Небольшое коммерческое помещение"},
        2: {"name": "🏥 Больница", "price": 150, "description": "Медицинское учреждение"},
        3: {"name": "🏛️ Музей", "price": 200, "description": "Культурное заведение"},
        4: {"name": "📮 Почта", "price": 120, "description": "Почтовое отделение"},
        5: {"name": "🏨 Отель", "price": 180, "description": "Гостиничный комплекс"}
    }

    return render_template(
        "pricing.html",
        rental_prices=rental_prices,
        student_name=student_name,
        student_group=student_group,
        current_user=session.get("name")
    )



# ------------------ Запуск ------------------

if __name__ == "__main__":
    app.run(debug=True, port=5001)