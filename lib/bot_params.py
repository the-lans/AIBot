# Состояние, в котором находится пользователь
class BotState:
    START = "start"
    CLEAR = "clear"
    SYSTEM = "system"
    SYSTEM_STEP2 = "system_step2"
    VOICE = "voice"
    ANSWER = "answer"
    MODEL = "model"
    ECHO = "echo"
    MESSAGE = "message"


# Формат ответа
class BotAnswer:
    TEXT = ("Текст", "text")
    VOICE = ("Голос", "voice")
    ALL = ("Все", "all")


# Режим работы бота, его функционал
class BotEcho:
    ECHO = ("Эхобот", "echo")
    AI = ("Искусственный интеллект", "ai")


# Используемая модель ИИ
class BotAIModel:
    CHAT_GPT_35 = ("GPT-3.5 Turbo 16K", "gpt-3.5-turbo-1106")
    CHAT_GPT_4 = ("GPT-4 Turbo 128K", "gpt-4-1106-preview")
    DALLE3 = ("DALL-E 3", "dall-e-3")


class BotParams:
    def __init__(self):
        self.mode = BotState.START
        self.answer = BotAnswer.VOICE
        self.echo = BotEcho.AI
        self.model = BotAIModel.CHAT_GPT_35


def get_class_values(cls):
    class_values = [getattr(cls, attr) for attr in vars(cls) if not attr.startswith("__")]
    return class_values


def get_class_dict(cls):
    values = get_class_values(cls)
    if values and isinstance(values[0], str):
        merged_dict = {item.strip().capitalize(): item for item in values}
    else:
        merged_dict = {item[0]: item for item in values}
    return merged_dict


def is_value_in_class_values(value, cls):
    return value in get_class_values(cls)
