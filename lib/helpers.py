from functools import wraps
import re

from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

from lib.config import Config
from lib.users import UserStorage


bot = TeleBot(Config.API_KEY_TELEGRAM_BOT)
user_storage = UserStorage("users.json")
hide_markup = ReplyKeyboardRemove()


class StateHandlerDecorator:
    def __init__(self):
        self._handlers = {}

    def add_handler(self, state):
        def decorator(func):
            self._handlers[state] = func
            return func

        return decorator

    def handle(self, state, *args, **kwargs):
        if state in self._handlers:
            return self._handlers[state](*args, **kwargs)
        elif None in self._handlers:
            return self._handlers[None](*args, **kwargs)
        else:
            print(f"No handler found for state {state}")


def check_message(
    bot: "TeleBot", user_id: str, user_input: str, choises: list[str], is_markup: bool = True, msg_error: str = None
) -> bool:
    user_input = user_input.strip().lower()
    if user_input in map(lambda arg: arg.lower(), choises):
        return True
    if msg_error is None:
        msg_error = "Неверный ответ. Попробуйте ещё..."
    markup = None
    if is_markup:
        markup = ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(*choises)
    bot.send_message(user_id, msg_error, reply_markup=markup)
    return False


def send_message_admin(text: str):
    for user_id in Config.ADMIN_IDS:
        bot.send_message(user_id, text, reply_markup=hide_markup)


def check_start_user(message):
    user_id = message.chat.id
    if not user_storage.has_user(user_id):
        first_name = message.chat.first_name or "<неизвестно>"
        username = message.chat.username or "<без username>"
        user_storage.add_user(user_id, {"access": True, "first_name": first_name, "username": username})
        send_message_admin(f"Появился новый пользователь ID: {user_id}, имя: {first_name}, ник: {username}")


def check_user_access(user_id: str) -> bool:
    return user_storage.get_user(user_id).get("access", True)


# Декоратор для проверки админских прав
def admin_required(func):
    @wraps(func)
    def wrapped(message):
        user_id = message.chat.id
        if user_id in Config.ADMIN_IDS:
            return func(message)
        else:
            bot.send_message(user_id, "Извините, этой командой может пользоваться только администратор.")

    return wrapped


# Декоратор для обработки текста после команды
def parse_args(pattern):
    def decorator(func):
        @wraps(func)
        def wrapped(message):
            match = re.search(pattern, message.text)
            if not match:
                return bot.reply_to(message, "Неверный формат команды.")
            return func(message, *match.groups())

        return wrapped

    return decorator
