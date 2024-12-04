import telebot
import sqlite3
import uuid
import json
from telebot import types
from TeamScripts.qwiz import start_survey, handle_survey_response, active_surveys
from openai import OpenAI

# Токен вашего бота (замените на ваш)
BOT_TOKEN = "8172850469:AAEq_qPudr2H27sogDEQvRcqTwucqNMq-1E"
bot = telebot.TeleBot(BOT_TOKEN)

# Функция для подключения к базе данных
def get_db_connection():
    conn = sqlite3.connect('time_capsule.db')
    conn.row_factory = sqlite3.Row
    return conn

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
        # Пользователь — тимлид, проверяем, есть ли данные о команде
        cursor.execute("SELECT * FROM teams WHERE team_name = ?", (leader['team_name'],))
        team = cursor.fetchone()

        if not team or team['description'] is None:  # Если данных о команде нет, запрашиваем их
            msg1 = bot.reply_to(message, "Введите название команды:")
            bot.register_next_step_handler(msg1, lambda msg: process_team_name(msg, chat_id))
        else:
            # Обработка существующего тимлида с командой
            team_name = team['team_name']
            bot.reply_to(
                message,
                f"Здравствуйте, тимлид команды '{team_name}'.\n"
                f"Чтобы начать сбор капсулы времени, нажмите кнопку ниже."
            )
            # Кнопка для создания ссылки
            markup = types.InlineKeyboardMarkup()
            create_link_btn = types.InlineKeyboardButton("Собрать капсулу", callback_data=f"create_link_{team_name}")
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
            markup = types.InlineKeyboardMarkup()
            quiz_button = types.InlineKeyboardButton("Начать анкетирование", callback_data="start_quiz")
            markup.add(quiz_button)
            bot.send_message(chat_id, "Добро пожаловать! Нажмите кнопку ниже, чтобы начать анкетирование.", reply_markup=markup)
        else:
            # Регистрируем нового участника и связываем с командой
            cursor.execute("INSERT INTO users (chat_id, role, team_name) VALUES (?, 'member', ?)", (chat_id, team_name))
            conn.commit()

            bot.send_message(chat_id, f"Вы успешно присоединились к команде '{team_name}'!")
            markup = types.InlineKeyboardMarkup()
            quiz_button = types.InlineKeyboardButton("Начать анкетирование", callback_data="start_quiz")
            markup.add(quiz_button)
            bot.send_message(chat_id, "Добро пожаловать! Нажмите кнопку ниже, чтобы начать анкетирование.", reply_markup=markup)
    else:
        bot.reply_to(
            message,
            "Некорректная или недействительная ссылка. Обратитесь к вашему тимлиду."
        )
    conn.close()


def process_team_name(message, chat_id):
    team_name = message.text.strip()

    # Сохранение или обработка введенного названия команды
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams WHERE team_name = ?", (team_name,))
    existing_team = cursor.fetchone()

    if existing_team:
        bot.reply_to(message, "Такое название команды уже существует. Пожалуйста, введите другое.")
        return

    msg = bot.reply_to(message, "Введите описание вашей команды:")
    bot.register_next_step_handler(msg, process_team_description, team_name, chat_id)
    conn.close()


def process_team_description(message, team_name, chat_id):
    description = message.text.strip()

    # Сохранение нового описания команды
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO teams (team_name, description) VALUES (?, ?)", (team_name, description))
    cursor.execute("UPDATE users SET team_name = ? WHERE chat_id = ?", (team_name, chat_id))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"Команда '{team_name}' успешно создана с описанием.")

    # Отправка кнопки для сбора капсулы
    markup = types.InlineKeyboardMarkup()
    create_link_btn = types.InlineKeyboardButton("Собрать капсулу", callback_data=f"create_link_{team_name}")
    markup.add(create_link_btn)
    bot.send_message(chat_id, "Нажмите кнопку, чтобы собрать капсулу времени:", reply_markup=markup)

# Обработка нажатия кнопки "Собрать капсулу"
@bot.callback_query_handler(func=lambda call: call.data.startswith("create_link_"))
def handle_create_link(call):
    chat_id = call.message.chat.id
    team_name = call.data.split("create_link_")[1]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM teams WHERE team_name = ?", (team_name,))
    team = cursor.fetchone()

    if team and team['link']:
        # Если ссылка уже создана, показываем кнопку остановки
        markup = telebot.types.InlineKeyboardMarkup()
        stop_btn = telebot.types.InlineKeyboardButton(
            "Остановить сбор данных",
            callback_data=f"stop_survey_{team_name}"
        )
        markup.add(stop_btn)

        bot.edit_message_text(
            f"Ссылка для вашей команды '{team_name}':\n{team['link']}\n\n"
            "Когда все участники заполнят анкеты, нажмите кнопку остановки сбора данных.",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    else:
        # Существующий код создания ссылки...
        unique_id = str(uuid.uuid4())
        full_link = f"https://t.me/{bot.get_me().username}?start={unique_id}"

        if not team:
            cursor.execute("INSERT INTO teams (team_name, link, is_active) VALUES (?, ?, ?)",
                           (team_name, unique_id, 1))
        else:
            cursor.execute("UPDATE teams SET link = ? WHERE team_name = ?", (unique_id, team_name))

        conn.commit()

        # Добавляем кнопку остановки сразу после создания ссылки
        markup = telebot.types.InlineKeyboardMarkup()
        stop_btn = telebot.types.InlineKeyboardButton(
            "Остановить сбор данных",
            callback_data=f"stop_survey_{team_name}"
        )
        markup.add(stop_btn)

        bot.edit_message_text(
            f"Ссылка для вашей команды '{team_name}':\n{full_link}\n\n"
            "Когда все участники заполнят анкеты, нажмите кнопку остановки сбора данных.",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    conn.close()

# Обработка команды /admin (только для админа)
ADMIN_CHAT_ID = 222570978  # Замените на ваш чат_id

@bot.message_handler(commands=['admin'])
def admin_command(message):
    chat_id = message.chat.id

    if chat_id == ADMIN_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add("Добавить тимлида", "Удалить тимлида", "Редактировать тимлида")
        bot.reply_to(message, "Добро пожаловать в админку! Выберите действие:", reply_markup=markup)
    else:
        bot.reply_to(message, "У вас нет прав доступа к админке.")

@bot.message_handler(func=lambda message: message.text in ["Добавить тимлида", "Удалить тимлида", "Редактировать тимлида"])
def handle_admin_action(message):
    action = message.text
    chat_id = message.chat.id

    if action == "Добавить тимлида":
        msg = bot.reply_to(message, "Введите chat_id нового тимлида:")
        bot.register_next_step_handler(msg, process_add_leader)
    elif action == "Удалить тимлида":
        msg = bot.reply_to(message, "Введите chat_id тимлида для удаления:")
        bot.register_next_step_handler(msg, process_delete_leader)
    elif action == "Редактировать тимлида":
        msg = bot.reply_to(message, "Введите chat_id тимлида для редактирования:")
        bot.register_next_step_handler(msg, process_edit_leader)

def process_add_leader(message):
    chat_id = message.chat.id
    new_leader_id = message.text

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (chat_id, role, team_name) VALUES (?, ?, ?)", (new_leader_id, "leader", ""))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"Тимлид с chat_id {new_leader_id} добавлен.")

def process_delete_leader(message):
    chat_id = message.chat.id
    leader_id = message.text

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE chat_id = ? AND role = 'leader'", (leader_id,))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"Тимлид с chat_id {leader_id} удален.")

def process_edit_leader(message):
    chat_id = message.chat.id
    edit_leader_id = message.text
    msg = bot.reply_to(message, "Введите новое название команды для тимлида:")
    bot.register_next_step_handler(msg, lambda m: process_update_leader(m, edit_leader_id))

def process_update_leader(message, leader_id):
    new_team_name = message.text

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET team_name = ? WHERE chat_id = ? AND role = 'leader'", (new_team_name, leader_id))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"Тимлид с chat_id {leader_id} обновлен, новая команда: {new_team_name}.")

def get_db_connection():
    conn = sqlite3.connect('time_capsule.db')  # Замените на вашу бд
    conn.row_factory = sqlite3.Row
    return conn

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
                f"Вы зарегистрированы как {user['role']} в команде '{user['team_name']}'."
            )
            markup = types.InlineKeyboardMarkup()
            quiz_button = types.InlineKeyboardButton("Начать анкетирование", callback_data="start_quiz")
            markup.add(quiz_button)
            bot.send_message(chat_id, "Добро пожаловать! Нажмите кнопку ниже, чтобы начать анкетирование.", reply_markup=markup)
        else:
            # Регистрируем нового участника
            cursor.execute("INSERT INTO users (chat_id, role, team_name) VALUES (?, ?, ?)", (chat_id, 'member', team_name))
            conn.commit()
            bot.send_message(chat_id, f"Вы успешно присоединились к команде '{team_name}'!")
            markup = types.InlineKeyboardMarkup()
            quiz_button = types.InlineKeyboardButton("Начать анкетирование", callback_data="start_quiz")
            markup.add(quiz_button)
            bot.send_message(chat_id, "Добро пожаловать! Нажмите кнопку ниже, чтобы начать анкетирование.", reply_markup=markup)
    else:
        bot.reply_to(message, "Некорректная или недействительная ссылка. Обратитесь к вашему тимлиду.")
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data == "start_quiz")
def quiz_callback(call):
    chat_id = call.message.chat.id

    # Проверяем, к какой команде относится участник
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM users WHERE chat_id = ?", (chat_id,))
    user = cursor.fetchone()

    if not user:
        bot.send_message(chat_id, "Вы не зарегистрированы в команде. Обратитесь к вашему тимлиду.")
        conn.close()
        return

    team_name = user["team_name"]
    conn.close()

    # Запускаем анкетирование
    start_survey(bot, call.message, team_name)

@bot.message_handler(func=lambda message: message.chat.id in active_surveys)
def survey_response_handler(message):
    handle_survey_response(bot, message)


def stop_survey_for_team(team_name):
    """Останавливает опрос для указанной команды"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Обновляем статус активности команды
    cursor.execute("UPDATE teams SET is_active = 0 WHERE team_name = ?", (team_name,))
    conn.commit()

    # Получаем всех участников команды
    cursor.execute("SELECT chat_id FROM users WHERE team_name = ?", (team_name,))
    team_members = cursor.fetchall()

    conn.close()
    return team_members


# Обработчик нажатия кнопки остановки опроса
@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_survey_"))
def handle_stop_survey(call):
    chat_id = call.message.chat.id
    team_name = call.data.split("stop_survey_")[1]

    # Проверяем, является ли пользователь тимлидом данной команды
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE chat_id = ? AND role = 'leader' AND team_name = ?",
                   (chat_id, team_name))
    leader = cursor.fetchone()
    conn.close()

    if not leader:
        bot.answer_callback_query(call.id, "У вас нет прав для остановки опроса!")
        return

    # Останавливаем опрос
    team_members = stop_survey_for_team(team_name)

    # Уведомляем всех участников команды
    for member in team_members:
        try:
            bot.send_message(member['chat_id'],
                             "Сбор данных для капсулы времени завершен тимлидом команды.")
        except:
            continue

    # Уведомляем тимлида
    bot.edit_message_text(
        f"Сбор данных для команды '{team_name}' завершен.\nНачинается обработка результатов...",
        chat_id=chat_id,
        message_id=call.message.message_id
    )

    # Здесь можно добавить вызов модуля для отправки данных в GPT
    process_survey_results(team_name)


def process_survey_results(team_name):
    """Обрабатывает результаты опроса и отправляет их в GPT"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем все ответы команды
    cursor.execute("""
        SELECT u.chat_id, u.role, s.response_data 
        FROM responses s 
        JOIN users u ON s.user_id = u.chat_id 
        JOIN teams t ON s.team_id = t.id 
        WHERE t.team_name = ?;
    """, (team_name,))

    responses = cursor.fetchall()
    conn.close()
    print(responses)


    # Форматируем данные для отправки в GPT
    formatted_data = format_responses_for_gpt(responses)
    print(formatted_data)
    # Получаем лидерский чат_id
    leader_chat_id = get_leader_chat_id(team_name)

    # Отправляем данные в GPT и отправляем ответ лидеру
    send_to_gpt(formatted_data, team_name, leader_chat_id)


# def format_responses_for_gpt(responses):
#     """Форматирует ответы для отправки в GPT"""
#     formatted = {
#         "team_responses": []
#     }
#
#     for response in responses:
#         # Предполагаем, что response_data хранится как JSON, извлекаем его
#         response_data = json.loads(response['response_data'])
#
#         formatted["team_responses"].append({
#             "user_role": response['role'],
#             "responses": response_data
#         })
#
#     return formatted


def get_leader_chat_id(team_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM users WHERE team_name = ? AND role = 'leader'", (team_name,))
    leader = cursor.fetchone()
    conn.close()
    return leader['chat_id'] if leader else None

def format_responses_for_gpt(responses):
    """Форматирует ответы для отправки в GPT"""
    formatted = {
        "team_responses": []
    }

    for response in responses:
        try:
            # Декодируем JSON из response_data
            response_data = json.loads(response['response_data'])

            # Добавляем ответы участника в общий список
            formatted["team_responses"].append({
                "user_role": response['role'],
                "responses": response_data
            })
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Ошибка при обработке response_data: {response['response_data']} - {e}")
            continue

    return formatted



def prepare_data_for_gpt(formatted_data):
    """Преобразует данные для использования в GPT"""
    questions = ["Вопрос 1", "Вопрос 2", "Вопрос 3", "Вопрос 4", "Вопрос 5"]
    result = {}

    # Объединяем ответы по каждому вопросу
    for i, question in enumerate(questions):
        result[question] = ", ".join([
            user["responses"][i] for user in formatted_data["team_responses"] if i < len(user["responses"])
        ])

    return result


# Установите ваш API-ключ OpenAI (убедитесь, что он защищен).
openai = OpenAI(api_key="sk-jbGuTUUPygaYe4ZV9SFNt6TnyJCEG51G",
                base_url="https://api.proxyapi.ru/openai/v1")


def send_to_gpt(formatted_data, team_name, leader_chat_id):
    try:
        # Подготавливаем данные для GPT
        data_for_gpt = prepare_data_for_gpt(formatted_data)

        # Преобразуем данные в текст
        formatted_text = "\n".join([f"{question}: {answers}" for question, answers in data_for_gpt.items()])

        # Получаем описание команды
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM teams WHERE team_name = ?", (team_name,))
        team = cursor.fetchone()
        description = team['description'] if team else 'Описание отсутствует'
        conn.close()

        # Формируем промпт
        prompt = f"""Ты пишешь письмо себе в будущее. Используй название команды и суть ее работы:{description} 
        Возьми ответы команды {team_name} на опрос:

{formatted_text}
1. Ты хочешь передать настроение момента и предостеречь себя от ошибок.
2. На основе ответов на 1 вопрос расскажи про свои ценности и почему они важны.
3. На основе ответов на 2 вопрос расскажи, за что ты благодарен товарищам.
4. На основе ответов на 4 вопрос расскажи, чего ждешь от следующего года.
5. В конце на основе ответов на 5 вопрос дай ироничный, но полезный совет самому себе.

В тексте используй иронию и немного пассивной агрессии.
Обращайся в письме к себе, как к старому другу.
Постарайся использовать локальные мемы (ответы на 3 вопрос) не как цитаты, а нативно.
Уложись в 1300 знаков.
Проверь предложения на согласованность."""

        # Обращение к модели GPT
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        # Извлекаем текст ответа GPT
        gpt_response_text = response.choices[0].message.content

        # Отправляем ответ тимлиду
        bot.send_message(leader_chat_id, f"Текст для капсулы времени:\n\n{gpt_response_text}")

    except Exception as e:
        # Если произошла ошибка, отправляем сообщение тимлиду
        bot.send_message(leader_chat_id, "Произошла ошибка при обработке данных опроса.")
        print(f"Ошибка при отправке в GPT: {e}")

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
