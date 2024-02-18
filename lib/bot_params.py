class BotState:
    START = "start"
    CLEAR = "clear"
    SYSTEM = "system"
    SYSTEM_STEP2 = "system_step2"
    VOICE = "voice"
    ANSWER = "answer"
    ECHO = "echo"
    MESSAGE = "message"


class BotAnswer:
    TEXT = "текст"
    VOICE = "голос"
    ALL = "все"


class BotEcho:
    ECHO = "echo"
    AI = "ai"


class BotParams:
    def __init__(self):
        self.mode = BotState.START
        self.answer = BotAnswer.VOICE
        self.echo = BotEcho.AI


def get_class_values(cls):
    class_values = [getattr(cls, attr) for attr in vars(cls) if not attr.startswith("__")]
    return class_values


def is_value_in_class_values(value, cls):
    return value in get_class_values(cls)
