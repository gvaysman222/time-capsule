from openai import OpenAI
import json
from database import get_db_connection

# Настройка OpenAI
client = OpenAI(api_key="sk-jbGuTUUPygaYe4ZV9SFNt6TnyJCEG51G",
                base_url="https://api.proxyapi.ru/openai/v1")  # Укажите ваш API-ключ OpenAI

def send_to_gpt(bot, capsule_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем данные капсулы
    cursor.execute("SELECT team_name, leader_id FROM capsules WHERE id = ?", (capsule_id,))
    capsule = cursor.fetchone()

    if not capsule:
        print(f"Капсула с ID {capsule_id} не найдена.")
        return

    team_name = capsule["team_name"]
    leader_id = capsule["leader_id"]

    # Получаем ответы участников
    cursor.execute("SELECT user_id, response_data FROM responses WHERE capsule_id = ?", (capsule_id,))
    responses = cursor.fetchall()
    conn.close()

    if not responses:
        bot.send_message(leader_id, f"Нет данных опросов для капсулы '{team_name}'.")
        return

    # Формируем данные для GPT
    formatted_responses = []
    for response in responses:
        user_id = response["user_id"]
        try:
            answers = json.loads(response["response_data"])
        except json.JSONDecodeError:
            answers = ["Ошибка декодирования данных"]
        formatted_responses.append(f"Пользователь {user_id}:\n" + "\n".join(f" - {a}" for a in answers))


    prompt = f"""
Капсула времени для команды '{team_name}' завершена. Вот ответы участников:

{chr(10).join(formatted_responses)}

В преддверии нового года твоя команда решила написать письмо в будущее, чтобы через год прочитать его и посмотреть что изменилось. Все ответы собраны в таблице. Ты должен проанализировать ответы и на их основе создать текст письма. Так будто письмо написано одним участником команды самому себе.
Вот такие требования к тексту письма:
1.  Обратись в письме к себе, как к старому другу.
2.  Передай настроение предвкушения нового года.
3.  Используй иронию и сарказм.
4.  Расскажи про свои ценности и почему они важны
5.  Расскажи за что ты благодарен товарищам
6.  Расскажи чего ждешь от следующего года. 
7.  В конце дай ироничный, но полезный совет самому себе, чтобы ожидания оправдались.
8.  Постарайся использовать локальные мемы нативно.
9.  Уложись в 1500 знаков.
    """

    # Отправляем данные в GPT
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        gpt_response = response.choices[0].message.content

        # Сохраняем письмо в базе данных
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE capsules SET capsule_mail = ? WHERE id = ?",
            (gpt_response, capsule_id)
        )
        conn.commit()
        conn.close()

        # Отправляем ответ тимлиду
        bot.send_message(
            leader_id,
            f"Команда '{team_name}', ваша капсула времени:\n\n{gpt_response}"
        )

    except Exception as e:
        print(f"Ошибка при отправке в GPT: {e}")
        bot.send_message(leader_id, "Произошла ошибка при обработке данных капсулы.")
