from functools import wraps
import logging
import re
import threading
from typing import Any, Optional, Union

from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

from lib.config import Config
from lib.errors import NotFoundHandler
from lib.users import UserStorage


logger = logging.getLogger(__name__)
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
            try:
                result = self._handlers[state](*args, **kwargs)
            except Exception as ex:
                logger.error("Error handler %s: %s", state, ex)
                raise
            return result
        elif None in self._handlers:
            try:
                result = self._handlers[None](*args, **kwargs)
            except Exception as ex:
                logger.error("Error else-handler: %s", ex)
                raise
            return result
        else:
            ex = NotFoundHandler(state)
            logger.error(ex)
            raise ex


def check_message(
    bot: "TeleBot",
    user_id: str,
    user_input: str,
    choises: list[str],
    is_markup: Union[bool, list] = True,
    msg_error: str = None,
) -> bool:
    user_input = user_input.strip().lower()
    if user_input in map(lambda arg: arg.lower(), choises):
        return True
    if msg_error is None:
        msg_error = "Неверный ответ. Попробуйте ещё..."
    markup = None
    if isinstance(is_markup, list):
        markup = ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(*is_markup)
    elif is_markup is True:
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
        msg = f"Появился новый пользователь ID: {user_id}, имя: {first_name}, ник: {username}"
        logger.info(msg)
        send_message_admin(msg)


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


# Обрезка длинного сообщения
def cut_long_message(msg: str, length: int) -> str:
    return msg[:length] + "..." if len(msg) > length else msg


# Декоратор для команды с учётом таймаута
def command_with_timeout(timeout):
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.chat.id
            text = message.text

            def thread_function():
                try:
                    func(message, *args, **kwargs)
                except Exception as ex:
                    error_text = cut_long_message(str(ex), 512)
                    logger.error(ex)
                    bot.send_message(user_id, f"Команда не была выполнена из-за ошибки: {error_text}")

            thread = threading.Thread(target=thread_function)
            thread.start()
            thread.join(timeout=timeout)
            if thread.is_alive():
                bot.send_message(user_id, "Команда не была выполнена из-за таймаута!")
                if text.startswith("/"):
                    logger.error(f"Таймаут команды {text} истёк, прекращаем её выполнение!")
                else:
                    logger.error(f"Таймаут обработчика истёк, прекращаем его выполнение!")

        return wrapper

    return decorator


# Проверяет сообщение на вхождение его в цепочку
def is_message_chain(message) -> bool:
    user_input = message.text
    if user_input.startswith("+\n") or len(user_input) > 3580:
        return True
    return False


# Выбирает другое значение из списка
def get_alternative_value(lst: Union[list, tuple], val: Any) -> Optional[Any]:
    alternative_list = list(lst)
    alternative_list.remove(val)
    return alternative_list[0] if alternative_list else None
