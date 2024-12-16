from telebot import types
from database import get_db_connection
import uuid
from yookassa import Configuration, Payment

Configuration.account_id = "999342"  # Замените на ваш shopId
Configuration.secret_key = "test_oqJzffEIfPKYpd2RJaE4HSsrRYoYwUoam3rr8VlXIxw"  # Замените на ваш секретный ключ

def register_start_handlers(bot):
    @bot.message_handler(commands=['start'])
    def start_command(message):
        chat_id = message.chat.id
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, есть ли параметр в команде /start
        args = message.text.split()
        if len(args) > 1:
            unique_id = args[1]
            cursor.execute("SELECT * FROM capsules WHERE link = ? AND is_active = 1", (unique_id,))
            capsule = cursor.fetchone()

            if capsule:
                handle_capsule_join(bot, chat_id, capsule, cursor, conn)
            else:
                bot.reply_to(message, "Некорректная или недействительная ссылка.")
        else:
            # Проверяем роль пользователя
            cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
            user = cursor.fetchone()

            if user:
                if user['role'] == 'leader':
                    show_leader_menu(bot, chat_id)
                elif user['role'] == 'member':
                    bot.send_message(chat_id, "Вы зарегистрированы как участник команды.")
                else:
                    show_guest_menu(bot, chat_id)  # Для пользователей без роли
            else:
                show_guest_menu(bot, chat_id)  # Меню для новых пользователей

        conn.close()

    # Обработчик для присоединения к капсуле
    def handle_capsule_join(bot, chat_id, capsule, cursor, conn):
        cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        user = cursor.fetchone()

        if user and user['role'] == 'leader' and capsule['leader_id'] == chat_id:
            bot.send_message(chat_id, "Вы являетесь лидером этой капсулы и не можете присоединиться как участник.")
            show_leader_menu(bot, chat_id)
        else:
            cursor.execute(
                "INSERT OR REPLACE INTO users (chat_id, role, capsule_id) VALUES (?, 'member', ?)",
                (chat_id, capsule['id'])
            )
            conn.commit()
            bot.send_message(chat_id, f"Вы успешно присоединились к капсуле '{capsule['team_name']}'.")
            markup = types.InlineKeyboardMarkup()
            start_quiz_btn = types.InlineKeyboardButton("Пройти квиз", callback_data=f"start_quiz_{capsule['id']}")
            markup.add(start_quiz_btn)
            bot.send_message(chat_id, "Нажмите кнопку ниже, чтобы пройти квиз:", reply_markup=markup)

    # Меню для гостей (новых пользователей)
    def show_guest_menu(bot, chat_id):
        description = (
            "🤖 *Добро пожаловать в наш бот!*\n\n"
            "Здесь вы можете создавать капсулы времени для команд, проводить опросы и сохранять важные данные.\n\n"
            "💼 *Функции бота:*\n"
            "1️⃣ Создание и управление капсулами времени.\n"
            "2️⃣ Проведение командных опросов.\n"
            "3️⃣ Генерация писем для участников.\n\n"
            "💰 *Стоимость доступа:* 50 рублей.\n"
            "Нажмите кнопку ниже, чтобы приобрести доступ и начать пользоваться ботом."
        )

        markup = types.InlineKeyboardMarkup()
        buy_access_btn = types.InlineKeyboardButton("🔑 Купить доступ", callback_data="buy_access")
        markup.add(buy_access_btn)

        bot.send_message(chat_id, description, parse_mode="Markdown", reply_markup=markup)

    # Покупка доступа
    def create_payment(chat_id, description, amount, payment_type):
        """
        Функция для создания платежа через ЮKassa.
        """
        try:
            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",  # Сумма в рублях
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://your-return-url.com/"  # Укажите реальный URL возврата
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "chat_id": chat_id,  # Передаем chat_id для идентификации пользователя
                    "type": payment_type  # Передаем тип платежа
                }
            }, uuid.uuid4())

            return payment.confirmation.confirmation_url  # Возвращаем ссылку на оплату
        except Exception as e:
            print(f"Ошибка при создании платежа: {e}")
            return None

            return payment.confirmation.confirmation_url  # Возвращаем ссылку на оплату
        except Exception as e:
            print(f"Ошибка при создании платежа: {e}")
            return None

    @bot.callback_query_handler(func=lambda call: call.data == "buy_access")
    def buy_access(call):
        chat_id = call.message.chat.id
        payment_url = create_payment(chat_id, "Покупка доступа", 100.00, "buy_access")

        if payment_url:
            markup = types.InlineKeyboardMarkup()
            payment_button = types.InlineKeyboardButton("Оплатить 100 рублей", url=payment_url)
            markup.add(payment_button)
            bot.send_message(chat_id, "Перейдите по ссылке для оплаты:", reply_markup=markup)
        else:
            bot.send_message(chat_id, "Произошла ошибка при создании платежа. Обратитесь к администратору.")


def show_leader_menu(bot, chat_id):
    markup = types.InlineKeyboardMarkup()
    create_capsule_btn = types.InlineKeyboardButton("Создать капсулу", callback_data="create_capsule")
    my_capsules_btn = types.InlineKeyboardButton("Мои капсулы", callback_data="my_capsules")
    my_balance_btn = types.InlineKeyboardButton("Мой баланс", callback_data="my_balance")
    markup.add(create_capsule_btn, my_capsules_btn, my_balance_btn)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)
