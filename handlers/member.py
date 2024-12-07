from telebot import types
from database import get_db_connection

def register_member_handlers(bot):
    @bot.message_handler(commands=['start'])
    def join_capsule_command(message):
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Пожалуйста, используйте ссылку, предоставленную тимлидом.")
            return

        unique_id = args[1]
        chat_id = message.chat.id
        print(f"Получен уникальный ID: {unique_id}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем ссылку
        cursor.execute("SELECT * FROM capsules WHERE link = ? AND is_active = 1", (unique_id,))
        capsule = cursor.fetchone()
        print(f"Найденная капсула: {capsule}")

        if capsule:
            # Проверяем, не зарегистрирован ли пользователь уже
            cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
            user = cursor.fetchone()
            print(f"Пользователь найден: {user}")

            if user:
                bot.send_message(chat_id, "Вы уже зарегистрированы в команде.")
                return

            # Привязываем пользователя к капсуле
            cursor.execute("INSERT INTO users (chat_id, role, capsule_id) VALUES (?, 'member', ?)", (chat_id, capsule['id']))
            conn.commit()

            # Отправляем приветствие с кнопкой для запуска квиза
            markup = types.InlineKeyboardMarkup()
            start_quiz_btn = types.InlineKeyboardButton("Пройти квиз", callback_data=f"start_quiz_{capsule['id']}")
            markup.add(start_quiz_btn)
            bot.send_message(
                chat_id,
                f"Вы успешно присоединились к капсуле '{capsule['team_name']}'!\nНажмите кнопку ниже, чтобы пройти квиз:",
                reply_markup=markup
            )
        else:
            bot.reply_to(message, "Некорректная или недействительная ссылка.")
        conn.close()

    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_quiz_"))
    def start_quiz(call):
        chat_id = call.message.chat.id
        capsule_id = int(call.data.split("start_quiz_")[1])
        print(f"Квиз начат для капсулы ID: {capsule_id}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, привязан ли пользователь к капсуле
        cursor.execute("SELECT * FROM users WHERE chat_id = ? AND capsule_id = ?", (chat_id, capsule_id))
        user = cursor.fetchone()
        print(f"Пользователь для квиза: {user}")

        if user:
            bot.send_message(chat_id, "Начинаем квиз! Введите ответ на первый вопрос:")
            # Логика квиза начинается здесь — вы можете отправлять вопросы и записывать ответы
        else:
            bot.reply_to(call.message, "Вы не привязаны к этой капсуле.")
        conn.close()
