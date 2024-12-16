import sqlite3
import json
from handlers.start import show_leader_menu
# Вопросы для квиза
QUESTIONS = [
    "Делать крутые штуки нам помогают общие ценности. Как думаешь какие?",
    "Наверняка тебе есть за что поблагодарить товарищей. Поделись этим, пожалуйста.",
    "Поделись локальным мемом или фразой",
    "Во что ты веришь и на что надеешься в следующем году?",
    "Что бы ты посоветовал или пожелал будущему себе?"
]

# Активные сессии квиза
active_surveys = {}

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('time_capsule.db')
    conn.row_factory = sqlite3.Row
    return conn

# Начало квиза
def start_survey(bot, message, capsule_id):
    chat_id = message.chat.id

    # Проверяем, есть ли активная анкета
    if chat_id in active_surveys:
        # Сбрасываем состояние старого квиза
        active_surveys[chat_id] = {
            "capsule_id": capsule_id,
            "responses": [],
            "current_question": 0
        }
        bot.send_message(chat_id, "Вы начали новый квиз. Предыдущий прогресс был сброшен.")
    else:
        # Инициализация новой анкеты
        active_surveys[chat_id] = {
            "capsule_id": capsule_id,
            "responses": [],
            "current_question": 0
        }

    # Отправляем первый вопрос
    bot.send_message(chat_id, QUESTIONS[0])


# Обработка ответов
def handle_survey_response(bot, message):
    chat_id = message.chat.id

    if chat_id not in active_surveys:
        bot.reply_to(message, "У вас нет активной анкеты. Обратитесь к вашему тимлиду.")
        return

    survey = active_surveys[chat_id]
    responses = survey["responses"]
    capsule_id = survey["capsule_id"]

    # Сохраняем ответ на текущий вопрос
    responses.append(message.text)

    # Переходим к следующему вопросу
    current_question = len(responses)

    if current_question < len(QUESTIONS):
        bot.send_message(chat_id, QUESTIONS[current_question])
    else:
        save_survey_responses(chat_id, capsule_id, responses)
        bot.send_message(chat_id, "Спасибо за участие! Ваши ответы сохранены.")
        del active_surveys[chat_id]
        notify_leader_and_show_menu(bot, capsule_id)


# Сохранение ответов
def save_survey_responses(chat_id, capsule_id, responses):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Преобразуем ответы в JSON-формат
    responses_json = json.dumps(responses, ensure_ascii=False)

    # Вставляем данные в таблицу responses
    cursor.execute(
        "INSERT INTO responses (capsule_id, user_id, response_data) VALUES (?, ?, ?)",
        (capsule_id, chat_id, responses_json)
    )

    conn.commit()
    conn.close()

def check_all_responses_completed(capsule_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем общее количество пользователей и ответов для капсулы
    cursor.execute("SELECT COUNT(*) AS total_users FROM users WHERE capsule_id = ?", (capsule_id,))
    total_users = cursor.fetchone()["total_users"]

    cursor.execute("SELECT COUNT(*) AS total_responses FROM responses WHERE capsule_id = ?", (capsule_id,))
    total_responses = cursor.fetchone()["total_responses"]

    conn.close()
    return total_users == total_responses

# Уведомление лидера и показ меню
def notify_leader_and_show_menu(bot, capsule_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем данные капсулы
    cursor.execute("SELECT leader_id, team_name FROM capsules WHERE id = ?", (capsule_id,))
    capsule = cursor.fetchone()

    if capsule:
        leader_id = capsule["leader_id"]
        team_name = capsule["team_name"]

        # Уведомляем лидера
        bot.send_message(
            leader_id,
            f"Спасибо за квиз босс"
        )

        # Показываем меню для лидера
        show_leader_menu(bot, leader_id)

    conn.close()

