import uuid
from telebot import types
from database import get_db_connection

def register_leader_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "create_capsule")
    def create_capsule(call):
        chat_id = call.message.chat.id
        msg = bot.send_message(chat_id, "Введите название команды:")
        bot.register_next_step_handler(msg, process_team_name)

    def process_team_name(message):
        team_name = message.text.strip()
        chat_id = message.chat.id
        msg = bot.send_message(chat_id, "Введите описание команды:")
        bot.register_next_step_handler(msg, lambda msg: process_team_description(msg, team_name))

    def process_team_description(message, team_name):
        description = message.text.strip()
        chat_id = message.chat.id

        conn = get_db_connection()
        cursor = conn.cursor()

        # Генерация уникальной ссылки
        unique_id = str(uuid.uuid4())
        link = f"https://t.me/{bot.get_me().username}?start={unique_id}"

        # Сохранение капсулы в базу
        cursor.execute(
            "INSERT INTO capsules (leader_id, team_name, description, link) VALUES (?, ?, ?, ?)",
            (chat_id, team_name, description, unique_id)
        )
        capsule_id = cursor.lastrowid  # Получаем ID созданной капсулы

        conn.commit()
        conn.close()

        bot.send_message(chat_id, f"Капсула '{team_name}' создана! Вот ссылка для команды: {link}")

    @bot.callback_query_handler(func=lambda call: call.data == "my_capsules")
    def manage_capsules(call):
        chat_id = call.message.chat.id
        conn = get_db_connection()
        cursor = conn.cursor()

        # Получение всех капсул, созданных лидером
        cursor.execute("SELECT * FROM capsules WHERE leader_id = ?", (chat_id,))
        capsules = cursor.fetchall()

        if capsules:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for capsule in capsules:
                # Кнопка для выбора капсулы
                select_btn = types.InlineKeyboardButton(
                    f"{capsule['team_name']}",
                    callback_data=f"select_capsule_{capsule['id']}"
                )
                markup.add(select_btn)

            bot.send_message(chat_id, "Выберите капсулу для управления:", reply_markup=markup)
        else:
            bot.send_message(chat_id, "У вас пока нет созданных капсул.")
        conn.close()

    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_capsule_"))
    def manage_selected_capsule(call):
        chat_id = call.message.chat.id
        capsule_id = int(call.data.split("select_capsule_")[1])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Получение данных капсулы
        cursor.execute("SELECT * FROM capsules WHERE id = ?", (capsule_id,))
        capsule = cursor.fetchone()
        conn.close()

        if capsule:
            markup = types.InlineKeyboardMarkup(row_width=1)
            # Кнопки для выбранной капсулы
            quiz_btn = types.InlineKeyboardButton("Посмотреть квиз", callback_data=f"quiz_{capsule_id}")
            end_btn = types.InlineKeyboardButton("Завершить сбор", callback_data=f"end_{capsule_id}")
            markup.add(quiz_btn, end_btn)

            bot.edit_message_text(
                f"Капсула: {capsule['team_name']}\nЧто вы хотите сделать?",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        else:
            bot.reply_to(call.message, "Ошибка: капсула не найдена.")