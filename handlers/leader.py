import uuid
from telebot import types
from telebot.types import BotCommand
from database import get_db_connection
from TeamScripts.qwiz import start_survey, active_surveys, handle_survey_response
from GPTwork.GPTsummary import send_to_gpt
def register_leader_handlers(bot):
    # Установка кнопок меню для тимлидов
    def set_leader_commands(chat_id):
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, является ли пользователь тимлидом
        cursor.execute("SELECT role FROM users WHERE chat_id = ?", (chat_id,))
        user = cursor.fetchone()
        conn.close()

        if user and user['role'] == 'leader':
            # Устанавливаем команды только для тимлидов
            bot.set_my_commands([
                BotCommand("menu", "Показать меню лидера"),
                BotCommand("create_capsule", "Создать капсулу"),
                BotCommand("my_capsules", "Мои капсулы"),
            ], scope=types.BotCommandScopeChat(chat_id))

    # Команда /start
    @bot.message_handler(commands=['start'])
    def start_handler(message):
        chat_id = message.chat.id

        # Проверяем и устанавливаем команды для тимлида
        set_leader_commands(chat_id)

        bot.send_message(chat_id, "Добро пожаловать! Если вы тимлид, у вас есть доступ к специальным функциям.")

    # Создание капсулы
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

        # Проверка на существование записи с тем же chat_id и capsule_id
        cursor.execute("SELECT * FROM users WHERE chat_id = ? AND capsule_id = ?", (chat_id, capsule_id))
        user = cursor.fetchone()

        if not user:
            # Добавляем запись только если она уникальна по chat_id и capsule_id
            cursor.execute(
                "INSERT INTO users (chat_id, role, capsule_id) VALUES (?, 'leader', ?)",
                (chat_id, capsule_id)
            )

        conn.commit()
        conn.close()

        bot.send_message(chat_id, f"Капсула '{team_name}' создана! Вот ссылка для команды: {link}")

    # Управление капсулами
    @bot.callback_query_handler(func=lambda call: call.data == "my_capsules")
    def manage_capsules(call):
        chat_id = call.message.chat.id
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM capsules WHERE leader_id = ?", (chat_id,))
        capsules = cursor.fetchall()

        if capsules:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for capsule in capsules:
                select_btn = types.InlineKeyboardButton(
                    f"{capsule['team_name']}",
                    callback_data=f"select_capsule_{capsule['id']}"
                )
                markup.add(select_btn)

            bot.send_message(chat_id, "Выберите капсулу для управления:", reply_markup=markup)
        else:
            bot.send_message(chat_id, "У вас пока нет созданных капсул.")
        conn.close()

    # Управление выбранной капсулой
    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_capsule_"))
    def manage_selected_capsule(call):
        chat_id = call.message.chat.id
        capsule_id = int(call.data.split("select_capsule_")[1])

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM capsules WHERE id = ?", (capsule_id,))
        capsule = cursor.fetchone()
        conn.close()

        if capsule:
            markup = types.InlineKeyboardMarkup(row_width=1)
            quiz_btn = types.InlineKeyboardButton(
                f"Пройти квиз: {capsule['team_name']}",
                callback_data=f"quiz_{capsule['id']}"
            )
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

    # Запуск квиза
    @bot.callback_query_handler(func=lambda call: call.data.startswith("quiz_"))
    def start_quiz(call):
        chat_id = call.message.chat.id

        try:
            capsule_id = int(call.data.split("quiz_")[1])
        except ValueError:
            bot.reply_to(call.message, "Ошибка: Неверный идентификатор капсулы.")
            return

        start_survey(bot, call.message, capsule_id)

    # Завершение сбора
    @bot.callback_query_handler(func=lambda call: call.data.startswith("end_"))
    def end_survey(call):
        chat_id = call.message.chat.id
        capsule_id = int(call.data.split("end_")[1])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE capsules SET is_active = 0 WHERE id = ?", (capsule_id,))
        conn.commit()
        conn.close()

        bot.send_message(chat_id, "Сбор данных завершён. Ответы отправлены.")
        send_to_gpt(bot, capsule_id)

    # Регистрация обработчика для ответа на квиз
    @bot.message_handler(func=lambda message: message.chat.id in active_surveys)
    def process_survey_response(message):
        handle_survey_response(bot, message)
