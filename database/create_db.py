import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "storage.db")

def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            login TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cells (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            building_type INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    cursor.execute("SELECT COUNT(*) FROM cells;")
    cell_count = cursor.fetchone()[0]

    if cell_count == 0:
        cells = [(i, None, None) for i in range(1, 101)]
        cursor.executemany(
            "INSERT INTO cells (id, user_id, building_type) VALUES (?, ?, ?);",
            cells
        )
        print("Добавлены 100 ячеек.")

    conn.commit()
    conn.close()
    print("База данных успешно создана:", DB_PATH)


if __name__ == "__main__":
    create_database()