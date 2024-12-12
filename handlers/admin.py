from telebot import types
from database import get_db_connection

ADMIN_ID = 6248416489  # Укажите ваш Telegram ID

def register_admin_handlers(bot):
    @bot.message_handler(commands=['admin'])
    def admin_panel(message):
        if message.chat.id != ADMIN_ID:
            bot.reply_to(message, "У вас нет доступа к админской панели.")
            return

        # Отображаем админское меню
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        add_leader_btn = types.KeyboardButton("Добавить Тимлида")
        view_leaders_btn = types.KeyboardButton("Просмотреть Тимлидов")
        markup.add(add_leader_btn, view_leaders_btn)
        bot.send_message(message.chat.id, "Админская панель:", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.text == "Добавить Тимлида")
    def add_leader_step_1(message):
        bot.send_message(message.chat.id, "Введите ID пользователя, которого хотите сделать тимлидом:")
        bot.register_next_step_handler(message, add_leader_step_2)

    def add_leader_step_2(message):
        try:
            user_id = int(message.text.strip())
        except ValueError:
            bot.reply_to(message, "Некорректный ID. Попробуйте ещё раз.")
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, есть ли такой пользователь
        cursor.execute("SELECT * FROM users WHERE chat_id = ?", (user_id,))
        user = cursor.fetchone()

        if user:
            bot.reply_to(message, "Пользователь уже существует.")
        else:
            # Добавляем тимлида
            cursor.execute(
                "INSERT INTO users (chat_id, role, capsule_id) VALUES (?, 'leader', 1)",
                (user_id,)
            )
            conn.commit()
            bot.send_message(message.chat.id, f"Пользователь {user_id} добавлен как тимлид с капсулой ID 1.")
        conn.close()

    @bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.text == "Просмотреть Тимлидов")
    def view_leaders(message):
        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем всех тимлидов
        cursor.execute("SELECT chat_id FROM users WHERE role = 'leader'")
        leaders = cursor.fetchall()
        conn.close()

        if leaders:
            leader_list = "\n".join([f"ID: {leader['chat_id']}" for leader in leaders])
            bot.send_message(message.chat.id, f"Список тимлидов:\n{leader_list}")
        else:
            bot.send_message(message.chat.id, "Тимлиды отсутствуют.")
