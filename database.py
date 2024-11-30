import sqlite3

def initialize_db():
    # Подключение к базе данных (или создание новой)
    conn = sqlite3.connect('time_capsule.db')
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('leader', 'member', 'admin')),
            team_name TEXT
        )
    ''')

    # Таблица команд
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT UNIQUE NOT NULL,
            link TEXT UNIQUE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1
        )
    ''')

    # Таблица ответов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            response_data TEXT NOT NULL,
            FOREIGN KEY(team_id) REFERENCES teams(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("База данных успешно инициализирована.")

if __name__ == "__main__":
    initialize_db()
