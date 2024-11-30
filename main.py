import telebot
import sqlite3
import uuid
from TeamScripts.qwiz import start_survey, handle_survey_response


# Токен вашего бота (замените на ваш)
BOT_TOKEN = "5998611067:AAGAorkOfr0PRAn-vZWyUiKxWQ11MhsUUj8"
bot = telebot.TeleBot(BOT_TOKEN)

# Функция для подключения к базе данных
def get_db_connection():
    conn = sqlite3.connect('time_capsule.db')
    conn.row_factory = sqlite3.Row
    return conn

# Команда /start
# Команда /start
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    args = message.text.split()  # Извлекаем параметры команды (например, ссылку)

    # Подключение к базе данных
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, зарегистрирован ли пользователь как тимлид
    cursor.execute("SELECT * FROM users WHERE chat_id = ? AND role = 'leader'", (chat_id,))
    leader = cursor.fetchone()

    if leader:
        # Пользователь — тимлид, приветствуем его
        team_name = leader['team_name']
        cursor.execute("SELECT * FROM teams WHERE team_name = ?", (team_name,))
        team = cursor.fetchone()

        bot.reply_to(
            message,
            f"Здравствуйте, тимлид команды '{team_name}'.\n"
            f"Чтобы начать сбор капсулы времени, нажмите кнопку ниже."
        )
        # Кнопка для создания ссылки
        markup = telebot.types.InlineKeyboardMarkup()
        create_link_btn = telebot.types.InlineKeyboardButton("Собрать капсулу", callback_data=f"create_link_{team_name}")
        markup.add(create_link_btn)
        bot.send_message(chat_id, "Нажмите кнопку, чтобы начать сбор капсулы времени:", reply_markup=markup)
        conn.close()
        return

    # Если пользователь не тимлид, проверяем, есть ли параметр (ссылка)
    if len(args) < 2:
        bot.reply_to(
            message,
            "У вас нет доступа. Пожалуйста, используйте ссылку, которую вам предоставил ваш тимлид."
        )
        conn.close()
        return

    # Проверяем, валидна ли ссылка
    link = args[1]
    cursor.execute("SELECT * FROM teams WHERE link = ?", (link,))
    team = cursor.fetchone()

    if team:
        team_name = team['team_name']

        # Проверяем, зарегистрирован ли пользователь уже
        cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        user = cursor.fetchone()

        if user:
            bot.reply_to(
                message,
                f"Вы уже зарегистрированы как {user['role']} в команде '{user['team_name']}'."
            )
        else:
            # Регистрируем нового участника и связываем с командой
            cursor.execute("INSERT INTO users (chat_id, role, team_name) VALUES (?, ?, ?)", (chat_id, 'member', team_name))
            conn.commit()

            bot.send_message(chat_id, f"Вы успешно присоединились к команде '{team_name}'!")
    else:
        bot.reply_to(
            message,
            "Некорректная или недействительная ссылка. Обратитесь к вашему тимлиду."
        )
    conn.close()


# Обработка нажатия кнопки "Собрать капсулу"
@bot.callback_query_handler(func=lambda call: call.data.startswith("create_link_"))
def handle_create_link(call):
    chat_id = call.message.chat.id
    team_name = call.data.split("create_link_")[1]

    # Подключение к базе данных
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, существует ли команда с таким именем
    cursor.execute("SELECT * FROM teams WHERE team_name = ?", (team_name,))
    team = cursor.fetchone()

    if team and team['link']:
        # Если ссылка уже создана, уведомляем тимлида
        bot.answer_callback_query(call.id, "Ссылка уже создана для этой команды!")
    else:
        # Генерация уникальной ссылки
        unique_id = str(uuid.uuid4())
        full_link = f"https://t.me/{bot.get_me().username}?start={unique_id}"

        if not team:
            # Если команда не существует, создаём новую запись
            cursor.execute("INSERT INTO teams (team_name, link, is_active) VALUES (?, ?, ?)",
                           (team_name, full_link, 1))
        else:
            # Если команда существует, обновляем её ссылку
            cursor.execute("UPDATE teams SET link = ? WHERE team_name = ?", (full_link, team_name))

        conn.commit()

        # Уведомляем тимлида
        bot.edit_message_text(
            f"Ссылка для вашей команды '{team_name}' успешно создана:\n{full_link}",
            chat_id=chat_id,
            message_id=call.message.message_id
        )

    conn.close()


# Обработка команды /admin (только для админа)
@bot.message_handler(commands=['admin'])
def admin_command(message):
    chat_id = message.chat.id

    # Проверка chat_id админа (замените на ваш chat_id)
    ADMIN_CHAT_ID = 123456789  # Замените на свой chat_id
    if chat_id == ADMIN_CHAT_ID:
        bot.reply_to(message, "Добро пожаловать в админку!")
    else:
        bot.reply_to(message, "У вас нет прав доступа к админке.")

# Команда /start с параметром (участник использует ссылку для входа)
@bot.message_handler(commands=['start'])
def join_team_command(message):
    chat_id = message.chat.id
    args = message.text.split()

    # Если команда запущена без параметра (ссылки)
    if len(args) < 2:
        bot.reply_to(
            message,
            "У вас нет доступа. Пожалуйста, используйте ссылку, которую вам предоставил ваш тимлид."
        )
        return

    link = args[1]

    # Подключение к базе данных
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, существует ли команда с такой ссылкой
    cursor.execute("SELECT * FROM teams WHERE link = ? AND is_active = 1", (link,))
    team = cursor.fetchone()

    if team:
        team_name = team['team_name']

        # Проверяем, зарегистрирован ли пользователь уже
        cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        user = cursor.fetchone()

        if user:
            bot.reply_to(
                message,
                f"Вы уже зарегистрированы как {user['role']} в команде '{user['team_name']}'."
            )
        else:
            # Регистрируем нового участника
            cursor.execute("INSERT INTO users (chat_id, role, team_name) VALUES (?, ?, ?)", (chat_id, 'member', team_name))
            conn.commit()
            bot.send_message(chat_id, f"Вы успешно присоединились к команде '{team_name}'!")
    else:
        bot.reply_to(message, "Некорректная или недействительная ссылка. Обратитесь к вашему тимлиду.")
    conn.close()

@bot.message_handler(commands=['quiz'])
def quiz_command(message):
    chat_id = message.chat.id

    # Проверяем, к какой команде относится участник
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM users WHERE chat_id = ?", (chat_id,))
    user = cursor.fetchone()

    if not user:
        bot.reply_to(message, "Вы не зарегистрированы в команде. Обратитесь к вашему тимлиду.")
        conn.close()
        return

    team_name = user["team_name"]
    conn.close()

    # Запускаем анкетирование
    start_survey(bot, message, team_name)

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
