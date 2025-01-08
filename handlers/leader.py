import uuid
from telebot import types
from database import get_db_connection
from TeamScripts.qwiz import start_survey, active_surveys, handle_survey_response
from GPTwork.GPTsummary import send_to_gpt
from handlers.start import show_leader_menu
from telebot.types import LabeledPrice, PreCheckoutQuery, SuccessfulPayment
from yookassa import Configuration, Payment


Configuration.account_id = ""  # Замените на ваш shopId
Configuration.secret_key = ""  # Замените на ваш секретный ключ
CAPSULE_PRICE = 300
def register_leader_handlers(bot):
    def ensure_user_balance(chat_id):
        """Проверка наличия баланса у пользователя"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO balances (chat_id, balance) VALUES (?, 0)", (chat_id,))
        conn.commit()
        conn.close()

    @bot.callback_query_handler(func=lambda call: call.data == "create_capsule")
    def create_capsule(call):
        chat_id = call.message.chat.id
        ensure_user_balance(chat_id)

        # Проверка баланса
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM balances WHERE chat_id = ?", (chat_id,))
        balance = cursor.fetchone()["balance"]
        conn.close()

        if balance < CAPSULE_PRICE:
            # Недостаточно средств
            markup = types.InlineKeyboardMarkup()
            top_up_btn = types.InlineKeyboardButton("Пополнить баланс", callback_data="top_up_balance")
            back_btn = types.InlineKeyboardButton("Назад", callback_data="back_to_leader_menu")
            markup.add(top_up_btn, back_btn)

            bot.send_message(
                chat_id,
                f"❌ Недостаточно средств для создания капсулы.\n\n"
                f"💰 Ваш баланс: {balance} рублей.\n"
                f"💡 Стоимость создания капсулы: {CAPSULE_PRICE} рублей.",
                reply_markup=markup
            )
            return

        # Запрашиваем название команды
        msg = bot.send_message(chat_id, "Введите название команды:")
        bot.register_next_step_handler(msg, process_team_name)
    def process_team_name(message):
        team_name = message.text.strip()
        chat_id = message.chat.id
        bot.send_message(chat_id, "Введите описание команды:")
        bot.register_next_step_handler(message, lambda msg: process_team_description(msg, team_name))

    def process_team_description(message, team_name):
        description = message.text.strip()
        chat_id = message.chat.id

        # Генерация ссылки и обновление БД
        unique_id = str(uuid.uuid4())
        link = f"https://t.me/{bot.get_me().username}?start={unique_id}"

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO capsules (leader_id, team_name, description, link) VALUES (?, ?, ?, ?)",
                (chat_id, team_name, description, unique_id)
            )
            cursor.execute("UPDATE balances SET balance = balance - ? WHERE chat_id = ?", (CAPSULE_PRICE, chat_id))
            conn.commit()
            bot.send_message(
                chat_id,
                f"✅ Капсула '{team_name}' успешно создана!\nСсылка для команды: {link}"
            )
        except Exception as e:
            bot.send_message(chat_id, f"❌ Ошибка: {e}")
        finally:
            conn.close()

        show_leader_menu(bot, chat_id)

    @bot.callback_query_handler(func=lambda call: call.data == "my_capsules")
    def manage_capsules(call):
        chat_id = call.message.chat.id
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM capsules WHERE leader_id = ?", (chat_id,))
        capsules = cursor.fetchall()

        if capsules:
            markup = types.InlineKeyboardMarkup(row_width=1)
            back_btn = types.InlineKeyboardButton("Назад", callback_data="back_to_leader_menu")
            for capsule in capsules:
                select_btn = types.InlineKeyboardButton(
                    f"{capsule['team_name']}",
                    callback_data=f"select_capsule_{capsule['id']}"
                )
                markup.add(select_btn)
            markup.add(back_btn)

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

        cursor.execute("SELECT * FROM capsules WHERE id = ?", (capsule_id,))
        capsule = cursor.fetchone()
        conn.close()

        if capsule:
            # Проверяем статус капсулы
            is_active = capsule['is_active']

            # Генерация кнопок
            markup = types.InlineKeyboardMarkup(row_width=1)

            # Кнопка для повторной отправки ссылки (доступна всегда)
            repeat_link_btn = types.InlineKeyboardButton(
                "Повторить ссылку", callback_data=f"repeat_link_{capsule_id}"
            )
            markup.add(repeat_link_btn)

            if is_active:
                # Если капсула активна, показываем квиз и кнопку завершения сбора
                quiz_btn = types.InlineKeyboardButton(
                    f"Пройти квиз: {capsule['team_name']}",
                    callback_data=f"quiz_{capsule['id']}"
                )
                end_btn = types.InlineKeyboardButton(
                    "Завершить сбор", callback_data=f"end_{capsule_id}"
                )
                back_btn = types.InlineKeyboardButton("Назад", callback_data="back_to_leader_menu")
                markup.add(quiz_btn, end_btn, back_btn)
            else:
                # Если сбор завершён, добавляем кнопки для повторного письма и удаления капсулы
                repeat_email_btn = types.InlineKeyboardButton(
                    "Повторить письмо", callback_data=f"repeat_email_{capsule_id}"
                )
                delete_btn = types.InlineKeyboardButton(
                    "Удалить капсулу", callback_data=f"delete_capsule_{capsule_id}"
                )
                back_btn = types.InlineKeyboardButton("Назад", callback_data="back_to_leader_menu")
                markup.add(repeat_email_btn, delete_btn, back_btn)

            bot.edit_message_text(
                f"Капсула: {capsule['team_name']}\nЧто вы хотите сделать?",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        else:
            bot.reply_to(call.message, "Ошибка: капсула не найдена.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("quiz_"))
    def start_quiz(call):
        chat_id = call.message.chat.id

        try:
            capsule_id = int(call.data.split("quiz_")[1])  # Преобразуем в int
        except ValueError:
            bot.reply_to(call.message, "Ошибка: Неверный идентификатор капсулы.")
            return

        print(f"Начало квиза: chat_id={chat_id}, capsule_id={capsule_id}")  # Отладка

        # Запуск квиза
        start_survey(bot, call.message, capsule_id)

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
        show_leader_menu(bot, chat_id)

    # Регистрация обработчика для ответа на квиз
    @bot.message_handler(func=lambda message: message.chat.id in active_surveys)
    def process_survey_response(message):
        handle_survey_response(bot, message)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_capsule_"))
    def delete_capsule(call):
        chat_id = call.message.chat.id
        capsule_id = int(call.data.split("delete_capsule_")[1])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Удаляем капсулу и связанные данные
        cursor.execute("DELETE FROM capsules WHERE id = ?", (capsule_id,))
        cursor.execute("DELETE FROM users WHERE capsule_id = ?", (capsule_id,))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "Капсула удалена.")
        bot.send_message(chat_id, "Капсула успешно удалена.")
        show_leader_menu(bot, chat_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("repeat_link_"))
    def repeat_link(call):
        chat_id = call.message.chat.id
        capsule_id = int(call.data.split("repeat_link_")[1])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Извлекаем существующую ссылку из базы данных
        cursor.execute("SELECT link FROM capsules WHERE id = ?", (capsule_id,))
        capsule = cursor.fetchone()
        conn.close()

        if capsule and capsule['link']:
            # Отправляем сохранённую ссылку
            bot.send_message(chat_id, f"https://t.me/{bot.get_me().username}?start={capsule['link']}")
            show_leader_menu(bot, chat_id)
        else:
            bot.reply_to(call.message, "Ошибка: ссылка не найдена в базе данных. Обратитесь к администратору(")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("repeat_email_"))
    def repeat_email(call):
        chat_id = call.message.chat.id
        capsule_id = int(call.data.split("repeat_email_")[1])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Извлекаем письмо из базы данных
        cursor.execute("SELECT capsule_mail, team_name FROM capsules WHERE id = ?", (capsule_id,))
        capsule = cursor.fetchone()

        if capsule and capsule["capsule_mail"]:
            # Отправляем сохранённое письмо лидеру
            bot.send_message(
                chat_id,
                f"Команда '{capsule['team_name']}', ваша капсула времени:\n\n{capsule['capsule_mail']}"
            )
            bot.answer_callback_query(call.id, "Письмо отправлено повторно!")
        else:
            # Если письмо не найдено
            bot.answer_callback_query(call.id, "Письмо отсутствует. Возможно, капсула не завершена.")
            bot.send_message(chat_id, "Письмо ещё не создано. Завершите сбор, чтобы его сгенерировать.")

        conn.close()
        show_leader_menu(bot, chat_id)

    @bot.callback_query_handler(func=lambda call: call.data == "my_balance")
    def show_balance(call):
        chat_id = call.message.chat.id

        # Получение текущего баланса лидера
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM balances WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        conn.close()

        balance = result["balance"] if result else 0  # Если записи нет, баланс равен 0

        # Отправка баланса и отображение кнопок
        markup = types.InlineKeyboardMarkup(row_width=1)
        top_up_btn = types.InlineKeyboardButton("Пополнить баланс", callback_data="top_up_balance")
        back_btn = types.InlineKeyboardButton("Назад", callback_data="back_to_leader_menu")
        markup.add(top_up_btn, back_btn)

        bot.edit_message_text(
            f"Ваш текущий баланс: {balance} рублей.\nВыберите действие:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    # @bot.callback_query_handler(func=lambda call: call.data == "top_up_balance")
    # def top_up_balance(call):
    #     chat_id = call.message.chat.id
    #
    #     # Создание инвойса (50 рублей = 5000 копеек)
    #     prices = [LabeledPrice(label="Пополнение баланса", amount=5000)]
    #
    #     try:
    #         bot.send_invoice(
    #             chat_id=chat_id,
    #             title="Пополнение баланса",
    #             description="Пополнение баланса в приложении на сумму 50 рублей.",
    #             provider_token="381764678:TEST:104434",  # Проверьте ключ!
    #             currency="RUB",
    #             prices=prices,
    #             start_parameter="balance_recharge",
    #             invoice_payload="balance_50"
    #         )
    #         print("Инвойс отправлен успешно.")  # Логируем отправку
    #     except Exception as e:
    #         print(f"Ошибка при отправке инвойса: {e}")
    #         bot.send_message(chat_id, "Произошла ошибка при формировании счёта. Обратитесь к администратору.")

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

    @bot.callback_query_handler(func=lambda call: call.data == "top_up_balance")
    def top_up_balance(call):
        chat_id = call.message.chat.id
        payment_url = create_payment(chat_id, "Пополнение баланса", 300.00, "top_up_balance")

        if payment_url:
            markup = types.InlineKeyboardMarkup()
            payment_button = types.InlineKeyboardButton("Оплатить 300 рублей", url=payment_url)
            markup.add(payment_button)
            bot.send_message(chat_id, "Перейдите по ссылке для оплаты:", reply_markup=markup)
        else:
            bot.send_message(chat_id, "Произошла ошибка при создании платежа. Обратитесь к администратору.")

    # Обработчик pre_checkout_query
    @bot.pre_checkout_query_handler(func=lambda query: True)
    def checkout_handler(pre_checkout_query: PreCheckoutQuery):
        print(f"DEBUG: pre_checkout_query вызван с ID {pre_checkout_query.id}")
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

    # Обработчик успешного платежа
    @bot.message_handler(content_types=['successful_payment'])
    def successful_payment_handler(message):
        chat_id = message.chat.id

        try:
            # Обновляем баланс пользователя
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE balances SET balance = balance + 300 WHERE chat_id = ?",
                (chat_id,)
            )
            conn.commit()
            conn.close()

            bot.send_message(chat_id, "✅ Оплата успешно завершена! Ваш баланс пополнен на 300 рублей.")
            print(f"Баланс успешно обновлён для пользователя {chat_id}")
        except Exception as e:
            print(f"Ошибка при обновлении баланса: {e}")
            bot.send_message(chat_id, "❌ Произошла ошибка при обновлении баланса. Обратитесь к администратору.")
    @bot.callback_query_handler(func=lambda call: call.data == "back_to_leader_menu")
    def back_to_leader_menu(call):
        chat_id = call.message.chat.id

        # Возврат в меню лидера
        show_leader_menu(bot, chat_id)

