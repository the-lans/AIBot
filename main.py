from collections import defaultdict
from typing import Optional

from telebot import TeleBot
from telebot.types import BotCommand, ReplyKeyboardMarkup, ReplyKeyboardRemove

from lib.bot_params import BotAIModel, BotAnswer, BotEcho, BotParams, BotState, get_class_dict
from lib.config import Config
from lib.helpers import StateHandlerDecorator, check_message
from lib.openai import DialogueAI
from lib.speech import Speech, SpeechVoice


bot = TeleBot(Config.API_KEY_TELEGRAM_BOT)
dialogue = DialogueAI(Config.OPENAI_MODEL)
users_params = defaultdict(lambda: BotParams())
users_speech = defaultdict(lambda: Speech("marina"))
state_handler = StateHandlerDecorator()
hide_markup = ReplyKeyboardRemove()


@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    params = users_params[user_id]
    bot.send_message(
        user_id, "Привет! Я бот, который может поддержать разговор на любую тему.", reply_markup=hide_markup
    )
    params.mode = BotState.START


@bot.message_handler(commands=["clear"])
def send_clear(message):
    user_id = message.chat.id
    params = users_params[user_id]
    dialogue.clear(user_id)
    bot.send_message(user_id, "Очистил ваш диалог.", reply_markup=hide_markup)
    params.mode = BotState.CLEAR


@bot.message_handler(commands=["reset"])
def send_reset(message):
    user_id = message.chat.id
    dialogue.system(user_id)
    dialogue.clear(user_id)
    users_params[user_id] = params = BotParams()
    bot.send_message(user_id, "Сбросил ваш диалог.", reply_markup=hide_markup)
    params.mode = BotState.CLEAR


@bot.message_handler(commands=["system"])
def send_system(message):
    user_id = message.chat.id
    params = users_params[user_id]
    conversation_default = dialogue.get_system(user_id)
    bot.send_message(user_id, f'Системное сообщение: {conversation_default["content"]}', reply_markup=hide_markup)
    bot.send_message(
        user_id, "Напишите системное сообщение боту, которое задаёт стиль общения.", reply_markup=hide_markup
    )
    params.mode = BotState.SYSTEM


@state_handler.add_handler(BotState.SYSTEM)
def handle_system(user_id: str, user_input: str) -> Optional[bool]:
    params = users_params[user_id]
    dialogue.system(user_id, user_input)
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Да", "Нет")
    bot.send_message(user_id, "Сбросить ваш диалог?", reply_markup=markup)
    params.mode = BotState.SYSTEM_STEP2
    return False


@state_handler.add_handler(BotState.SYSTEM_STEP2)
def handle_system_step2(user_id: str, user_input: str) -> Optional[bool]:
    menu = {"Да": lambda: dialogue.clear(user_id), "Нет": lambda: dialogue.add_system(user_id)}
    if check_message(bot, user_id, user_input, list(menu.keys())):
        menu[user_input]()
        bot.send_message(user_id, "Системное сообщение записал!", reply_markup=hide_markup)
    else:
        return False


@bot.message_handler(commands=["voice"])
def send_voice(message):
    user_id = message.chat.id
    params = users_params[user_id]
    speech = users_speech[user_id]
    url = "https://cloud.yandex.ru/ru/docs/speechkit/tts/voices"
    bot.send_message(user_id, f"Голос: {speech.voice}. Введите название голоса: {url}", reply_markup=hide_markup)
    params.mode = BotState.VOICE


@state_handler.add_handler(BotState.VOICE)
def handle_voice(user_id: str, user_input: str) -> Optional[bool]:
    speech = users_speech[user_id]
    menu = get_class_dict(SpeechVoice)
    msg_error = "Нет такого голоса, попробуйте ещё..."
    if check_message(bot, user_id, user_input, list(menu.keys()), is_markup=False, msg_error=msg_error):
        speech.set_synthesis(user_input)
        bot.send_message(user_id, "Голос сохранил!", reply_markup=hide_markup)
    else:
        return False


@bot.message_handler(commands=["answer"])
def send_answer(message):
    user_id = message.chat.id
    params = users_params[user_id]
    answers = list(get_class_dict(BotAnswer).keys())
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(*answers)
    bot.send_message(
        user_id, f"Формат: {params.answer[0]}. Введите формат ответа: {', '.join(answers)}.", reply_markup=markup
    )
    params.mode = BotState.ANSWER


@state_handler.add_handler(BotState.ANSWER)
def handle_answer(user_id: str, user_input: str) -> Optional[bool]:
    params = users_params[user_id]
    menu = get_class_dict(BotAnswer)
    if check_message(bot, user_id, user_input, list(menu.keys())):
        params.answer = menu[user_input]
        bot.send_message(user_id, "Формат ответа сохранил!", reply_markup=hide_markup)
    else:
        return False


@bot.message_handler(commands=["model"])
def send_model(message):
    user_id = message.chat.id
    params = users_params[user_id]
    ai_models = get_class_dict(BotAIModel)
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(*list(ai_models.keys()))
    bot.send_message(user_id, f"Выберите модель ИИ.", reply_markup=markup)
    params.mode = BotState.MODEL


@state_handler.add_handler(BotState.MODEL)
def handle_model(user_id: str, user_input: str) -> Optional[bool]:
    params = users_params[user_id]
    menu = get_class_dict(BotAIModel)
    if check_message(bot, user_id, user_input, list(menu.keys())):
        params.model = menu[user_input]
        dialogue.user_model[user_id] = params.model[1]
        bot.send_message(user_id, "Модель ИИ изменил!", reply_markup=hide_markup)
    else:
        return False


@bot.message_handler(commands=["echo"])
def send_echo(message):
    user_id = message.chat.id
    params = users_params[user_id]
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Эхобот", "Искусственный интеллект")
    bot.send_message(user_id, "Выберите режим функционирования бота.", reply_markup=markup)
    params.mode = BotState.ECHO


@state_handler.add_handler(BotState.ECHO)
def handle_echo(user_id: str, user_input: str) -> Optional[bool]:
    params = users_params[user_id]
    menu = get_class_dict(BotEcho)
    if check_message(bot, user_id, user_input, list(menu.keys())):
        params.echo = menu[user_input]
        bot.send_message(user_id, "Режим изменил!", reply_markup=hide_markup)
    else:
        return False


@state_handler.add_handler(None)
def handle_output_message(user_id: str, user_input: str) -> Optional[bool]:
    params = users_params[user_id]
    speech = users_speech[user_id]
    ai_response_content = dialogue.generate(user_id, user_input) if params.echo == BotEcho.AI else user_input
    if params.answer in (BotAnswer.VOICE, BotAnswer.ALL):
        audio_stream = speech.synthesize(ai_response_content)
        bot.send_voice(user_id, audio_stream)
    if params.answer in (BotAnswer.TEXT, BotAnswer.ALL):
        bot.send_message(user_id, ai_response_content, parse_mode="Markdown", reply_markup=hide_markup)
    return None


def handle_input_message(message) -> Optional[str]:
    if message.content_type == "voice":
        user_id = message.chat.id
        speech = users_speech[user_id]
        file_info = bot.get_file(message.voice.file_id)
        audio_data = bot.download_file(file_info.file_path)
        user_input = speech.recognize(audio_data).strip()
        if user_input:
            bot.send_message(message.chat.id, user_input, parse_mode="Markdown", reply_markup=hide_markup)
        else:
            bot.send_message(
                message.chat.id, "Извините, я не смог распознать ваше сообщение.", reply_markup=hide_markup
            )
            return None
    else:
        user_input = message.text
    return user_input


@bot.message_handler(func=lambda message: True, content_types=["text", "voice"])
def handle_message(message):
    user_id = message.chat.id
    params = users_params[user_id]
    next_state = True

    # Распознавание входящего сообщения
    user_input = handle_input_message(message)
    if user_input is None:
        return

    # Функционал в зависимости от состояния
    result = state_handler.handle(params.mode, user_id, user_input)
    if result is not None:
        next_state = result
    if next_state:
        params.mode = BotState.MESSAGE


if __name__ == "__main__":
    bot.set_my_commands(
        [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("clear", "Очистить ваш диалог"),
            BotCommand("reset", "Сбросить в изначальное состояние"),
            BotCommand("system", "Изменить стиль общения"),
            BotCommand("voice", "Задать голос"),
            BotCommand("answer", "Формат ответа: текст или аудио"),
            BotCommand("model", "Выбор модели ИИ"),
            BotCommand("echo", "Режим эхобота"),
        ]
    )
    bot.infinity_polling()
