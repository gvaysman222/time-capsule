import telebot
from database import setup_database
from handlers.start import register_start_handlers
from handlers.leader import register_leader_handlers
from handlers.member import register_member_handlers
from handlers.admin import register_admin_handlers
# Ваш токен
BOT_TOKEN = ""
bot = telebot.TeleBot(BOT_TOKEN)

# Регистрация хендлеров
register_start_handlers(bot)
register_leader_handlers(bot)
register_member_handlers(bot)
register_admin_handlers(bot)
# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
