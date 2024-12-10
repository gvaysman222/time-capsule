import telebot
from database import setup_database
from handlers.start import register_start_handlers
from handlers.leader import register_leader_handlers
from handlers.member import register_member_handlers
from handlers.quiz import register_quiz_handlers

# Ваш токен
BOT_TOKEN = "5998611067:AAGAorkOfr0PRAn-vZWyUiKxWQ11MhsUUj8"
bot = telebot.TeleBot(BOT_TOKEN)

# Настройка базы данных
setup_database()

# Регистрация хендлеров
register_start_handlers(bot)
register_leader_handlers(bot)
register_member_handlers(bot)
register_quiz_handlers(bot)

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
