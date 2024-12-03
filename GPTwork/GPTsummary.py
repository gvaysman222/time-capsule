from openai import OpenAI

# Установите ваш API-ключ OpenAI (убедитесь, что он защищен).
openai = OpenAI(api_key="<KEY>",
                base_url="https://api.proxyapi.ru/openai")


def send_to_gpt(formatted_data, team_name, leader_chat_id):
    """Отправляет данные команды в GPT и отправляет ответ тимлиду."""
    try:
        # Подготавливаем данные JSON для отправки GPT
        prompt = f"""Вы являетесь анализатором данных. Вот ответы команды {team_name} на опрос:
        {formatted_data}

        Пожалуйста, обобщите их, выделив ключевые точки и предложите стратегии улучшения.
        """

        # Обращение к модели GPT
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )

        # Извлекаем ответ GPT
        gpt_response_text = response.choices[0].message.content

        # Отправляем ответ тимлиду
        bot.send_message(leader_chat_id, f"Текст для капсулы времени:\n{gpt_response_text}")

    except Exception as e:
        bot.send_message(leader_chat_id, "Произошла ошибка при обработке данных опроса.")
        print(f"Ошибка при отправке в GPT: {e}")