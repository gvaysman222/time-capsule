import telebot
from flask import Flask, request
from database import get_db_connection
from handlers.start import register_start_handlers, show_leader_menu
from handlers.leader import register_leader_handlers
from handlers.member import register_member_handlers
from handlers.admin import register_admin_handlers
import json
# Ваш токен и публичный URL для вебхука
BOT_TOKEN = "5998611067:AAGAorkOfr0PRAn-vZWyUiKxWQ11MhsUUj8"
WEBHOOK_URL = "https://e3b6-5-101-179-89.ngrok-free.app/" + BOT_TOKEN  # Замените на ваш ngrok URL

bot = telebot.TeleBot(BOT_TOKEN)

# Flask сервер для вебхука
app = Flask(__name__)

# Регистрация хендлеров
register_start_handlers(bot)
register_leader_handlers(bot)
register_member_handlers(bot)
register_admin_handlers(bot)

# Эндпоинт для обработки вебхука от Telegram
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    print(f"Получен запрос: {json_string}")  # Логируем запрос
    if not json_string.strip():
        print("Ошибка: тело запроса пустое.")
        return "Bad Request: Empty body", 400

    try:
        # Проверяем, является ли строка валидным JSON
        data = json.loads(json_string)
        print(f"Распарсенные данные: {data}")
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        return "Bad Request: Invalid JSON", 400

    try:
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        return "Internal Server Error", 500

    return "OK", 200




# Эндпоинт для установки вебхука
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    success = bot.set_webhook(url=WEBHOOK_URL)
    if success:
        return f"Webhook установлен: {WEBHOOK_URL}"
    return "Ошибка при установке вебхука"


# Эндпоинт для удаления вебхука
@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    success = bot.delete_webhook()
    if success:
        return "Webhook успешно удалён"
    return "Ошибка при удалении вебхука"


@app.route("/yookassa-webhook", methods=["POST"])
def yookassa_webhook():
    data = request.json
    print(f"Получено уведомление от ЮKассы: {data}")  # Логируем запрос для отладки

    if data and data.get("event") == "payment.succeeded":
        payment_object = data.get("object", {})
        payment_id = payment_object.get("id")
        chat_id = payment_object.get("metadata", {}).get("chat_id")
        payment_type = payment_object.get("metadata", {}).get("type")  # Тип платежа

        if not chat_id or not payment_type:
            print(f"Ошибка: chat_id или type отсутствуют в metadata платежа {payment_id}")
            return "Bad Request", 400

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Проверка наличия записи в таблице balances
                cursor.execute("SELECT * FROM balances WHERE chat_id = ?", (chat_id,))
                balance_record = cursor.fetchone()

                if not balance_record:
                    # Если записи нет, создаём её с начальными данными
                    cursor.execute(
                        "INSERT INTO balances (chat_id, balance) VALUES (?, 0)",
                        (chat_id,)
                    )
                    print(f"Создана запись для chat_id: {chat_id}")

                if payment_type == "buy_access":
                    # Проверяем, есть ли запись для этого chat_id и роли leader
                    cursor.execute("SELECT * FROM users WHERE chat_id = ? AND role = 'leader'", (chat_id,))
                    user = cursor.fetchone()

                    if not user:
                        # Добавляем новую запись, если роль leader отсутствует
                        cursor.execute(
                            "INSERT INTO users (chat_id, role, capsule_id) VALUES (?, 'leader', 0)",
                            (chat_id,)
                        )
                    else:
                        # Если запись уже существует, обновляем capsule_id на 0
                        cursor.execute(
                            "UPDATE users SET capsule_id = 0 WHERE chat_id = ? AND role = 'leader'",
                            (chat_id,)
                        )

                    # Пополняем баланс на 100 рублей
                    cursor.execute(
                        "UPDATE balances SET balance = balance + 100 WHERE chat_id = ?",
                        (chat_id,)
                    )

                    bot.send_message(chat_id, f"Спасибо за оплату! Теперь вы являетесь лидером. Ваш текущий баланс пополнен на 100 рублей.")
                    show_leader_menu(bot, chat_id)

                elif payment_type == "top_up_balance":
                    # Пополнение баланса
                    cursor.execute(
                        "UPDATE balances SET balance = balance + 50 WHERE chat_id = ?",
                        (chat_id,)
                    )
                    new_balance = cursor.execute("SELECT balance FROM balances WHERE chat_id = ?", (chat_id,)).fetchone()["balance"]
                    bot.send_message(chat_id, f"Ваш баланс успешно пополнен на 50 рублей. Текущий баланс: {new_balance} рублей.")

                conn.commit()
            print(f"Платеж {payment_id} успешно обработан для пользователя {chat_id}")
            return "OK", 200

        except Exception as e:
            print(f"Ошибка при обработке платежа: {e}")
            return "Internal Server Error", 500

    print("Ошибка: Неверный формат данных от ЮKассы.")
    return "Bad Request", 400



if __name__ == '__main__':
    print("Бот запущен...")
    # Запуск Flask сервера
    app.run(debug=True, port=8000)
