from telebot.types import ReplyKeyboardMarkup


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
