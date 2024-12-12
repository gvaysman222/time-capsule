from telebot import types
from database import get_db_connection

def register_start_handlers(bot):
    @bot.message_handler(commands=['start'])
    def start_command(message):
        chat_id = message.chat.id
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, есть ли параметр в команде /start
        args = message.text.split()
        if len(args) > 1:
            # Параметр ссылки
            unique_id = args[1]

            # Проверяем, существует ли капсула с таким идентификатором
            cursor.execute("SELECT * FROM capsules WHERE link = ? AND is_active = 1", (unique_id,))
            capsule = cursor.fetchone()

            if capsule:
                # Проверяем, зарегистрирован ли пользователь
                cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
                user = cursor.fetchone()

                if user:
                    if user['role'] == 'leader':
                        # Проверяем, существует ли уже запись как мембера для этой капсулы
                        cursor.execute(
                            "SELECT * FROM users WHERE chat_id = ? AND role = 'member' AND capsule_id = ?",
                            (chat_id, capsule['id'])
                        )
                        existing_member = cursor.fetchone()

                        if existing_member:
                            # Если запись уже существует, уведомляем пользователя
                            bot.send_message(chat_id,
                                             f"Вы уже добавлены в капсулу '{capsule['team_name']}' как участник.")
                        else:
                            # Если записи нет, создаём новую запись как мембера
                            cursor.execute(
                                "INSERT INTO users (chat_id, role, capsule_id) VALUES (?, 'member', ?)",
                                (chat_id, capsule['id'])
                            )
                            conn.commit()
                            bot.send_message(chat_id,
                                             f"Вы были добавлены в капсулу '{capsule['team_name']}' как участник.")
                    else:
                        # Если пользователь уже зарегистрирован как мембер, обновляем привязку
                        cursor.execute(
                            "UPDATE users SET capsule_id = ? WHERE chat_id = ?",
                            (capsule['id'], chat_id)
                        )
                        conn.commit()
                        bot.send_message(chat_id, f"Вы были перепривязаны к капсуле '{capsule['team_name']}'.")
                else:
                    # Если пользователь не зарегистрирован, создаём новую запись
                    cursor.execute(
                        "INSERT INTO users (chat_id, role, capsule_id) VALUES (?, 'member', ?)",
                        (chat_id, capsule['id'])
                    )
                    conn.commit()
                    bot.send_message(chat_id, f"Вы успешно присоединились к капсуле '{capsule['team_name']}'.")

                # Отправляем сообщение с кнопкой для квиза
                markup = types.InlineKeyboardMarkup()
                start_quiz_btn = types.InlineKeyboardButton("Пройти квиз", callback_data=f"start_quiz_{capsule['id']}")
                markup.add(start_quiz_btn)
                bot.send_message(
                    chat_id,
                    f"Нажмите кнопку ниже, чтобы пройти квиз:",
                    reply_markup=markup
                )
            else:
                bot.reply_to(message, "Некорректная или недействительная ссылка.")
        else:
            # Если параметра нет, проверяем роль пользователя
            cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
            user = cursor.fetchone()

            if user:
                if user['role'] == 'leader':
                    show_leader_menu(bot, chat_id)
                else:
                    bot.reply_to(message, "Вы зарегистрированы как участник команды.")
            else:
                bot.reply_to(
                    message,
                    "Добро пожаловать! Пожалуйста, используйте ссылку от тимлида для регистрации."
                )

        conn.close()

def show_leader_menu(bot, chat_id):
    markup = types.InlineKeyboardMarkup()
    create_capsule_btn = types.InlineKeyboardButton("Создать капсулу", callback_data="create_capsule")
    my_capsules_btn = types.InlineKeyboardButton("Мои капсулы", callback_data="my_capsules")
    markup.add(create_capsule_btn, my_capsules_btn)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)
