from telebot import types
import sqlite3
import json
from Commons.GoogleSheetWorker import write_responses_to_sheet

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('time_capsule.db')
    conn.row_factory = sqlite3.Row
    return conn

# Вопросы для анкеты
QUESTIONS = [
    "Делать крутые штуки нам помогают общие ценности. Как думаешь какие?",
    "Наверняка тебе есть за что поблагодарить товарищей. Поделись этим, пожалуйста.",
    "Поделись локальным мемом или фразой",
    "Во что ты веришь и на что надеешься в следующем году?",
    "Что бы ты посоветовал или пожелал будущему себе?"
]

# Хранилище текущих сессий анкетирования
active_surveys = {}

# Начало анкеты
def start_survey(bot, message, team_name):
    chat_id = message.chat.id
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, зарегистрирован ли пользователь как участник команды
    cursor.execute("SELECT * FROM users WHERE chat_id = ? AND team_name = ?", (chat_id, team_name))
    user = cursor.fetchone()

    if not user:
        bot.reply_to(message, "Вы не зарегистрированы в команде. Обратитесь к вашему тимлиду.")
        return

    # Инициализация анкеты
    active_surveys[chat_id] = {
        "team_name": team_name,
        "responses": [],
        "current_question": 0
    }

    # Отправка первого вопроса
    bot.send_message(chat_id, QUESTIONS[0])

# Обработка ответа
def handle_survey_response(bot, message):
    chat_id = message.chat.id

    # Проверяем, есть ли активная сессия анкеты
    if chat_id not in active_surveys:
        bot.reply_to(message, "У вас нет активной анкеты. Обратитесь к вашему тимлиду.")
        return

    survey = active_surveys[chat_id]
    team_name = survey["team_name"]

    # Сохраняем ответ на текущий вопрос
    survey["responses"].append(message.text)
    current_question = survey["current_question"] + 1

    # Если есть ещё вопросы
    if current_question < len(QUESTIONS):
        survey["current_question"] = current_question
        bot.send_message(chat_id, QUESTIONS[current_question])
    else:
        # Сохраняем ответы в базу данных
        save_survey_responses(chat_id, team_name, survey["responses"])

        # Завершаем анкетирование
        bot.send_message(chat_id, "Спасибо за участие! Ваши ответы сохранены.")
        del active_surveys[chat_id]

# Сохранение ответов в базу данных
def save_survey_responses(user_id, team_name, responses):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем имя пользователя
    cursor.execute("SELECT * FROM users WHERE chat_id = ?", (user_id,))
    user = cursor.fetchone()
    user_name = f"Пользователь {user_id}" if not user else user["chat_id"]

    # Сохраняем ответы в Google Таблицы
    write_responses_to_sheet(team_name, user_name, responses)

    # Также сохраняем в локальной базе данных
    cursor.execute("SELECT id FROM teams WHERE team_name = ?", (team_name,))
    team = cursor.fetchone()
    if not team:
        return

    team_id = team["id"]
    responses_json = json.dumps(responses)

    cursor.execute(
        "INSERT INTO responses (team_id, user_id, response_data) VALUES (?, ?, ?)",
        (team_id, user_id, responses_json)
    )
    conn.commit()
    conn.close()
