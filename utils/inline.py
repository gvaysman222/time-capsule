from telebot import types

def create_inline_menu(buttons):
    markup = types.InlineKeyboardMarkup()
    for text, callback_data in buttons:
        markup.add(types.InlineKeyboardButton(text, callback_data=callback_data))
    return markup
