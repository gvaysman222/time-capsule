import sqlite3

DB_NAME = 'time_capsule.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER UNIQUE,
        role TEXT NOT NULL,
        capsule_id INTEGER,
        FOREIGN KEY (capsule_id) REFERENCES capsules (id)
    )
    ''')

    # Таблица капсул
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS capsules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        leader_id INTEGER,
        team_name TEXT NOT NULL,
        description TEXT,
        link TEXT UNIQUE,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (leader_id) REFERENCES users (id)
    )
    ''')

    # Таблица ответов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        capsule_id INTEGER,
        response_data TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (capsule_id) REFERENCES capsules (id)
    )
    ''')

    conn.commit()
    conn.close()
