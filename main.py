from collections import defaultdict

from telebot import TeleBot
from telebot.types import BotCommand, ReplyKeyboardMarkup, ReplyKeyboardRemove

from lib.bot_params import BotAnswer, BotEcho, BotParams, BotState, get_class_values, is_value_in_class_values
from lib.config import Config
from lib.openai import DialogueAI
from lib.speech import Speech, SpeechVoice


bot = TeleBot(Config.API_KEY_TELEGRAM_BOT)
dialogue = DialogueAI(Config.OPENAI_MODEL)
users_params = defaultdict(lambda: BotParams())
users_speech = defaultdict(lambda: Speech("marina"))


@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    params = users_params[user_id]
    bot.send_message(user_id, "Привет! Я бот, который может поддержать разговор на любую тему.")
    params.mode = BotState.START


@bot.message_handler(commands=["clear"])
def send_clear(message):
    user_id = message.chat.id
    params = users_params[user_id]
    dialogue.clear(user_id)
    bot.send_message(user_id, "Очистил ваш диалог.")
    params.mode = BotState.CLEAR


@bot.message_handler(commands=["reset"])
def send_reset(message):
    user_id = message.chat.id
    dialogue.system(user_id)
    dialogue.clear(user_id)
    users_params[user_id] = params = BotParams()
    bot.send_message(user_id, "Сбросил ваш диалог.")
    params.mode = BotState.CLEAR


@bot.message_handler(commands=["system"])
def send_system(message):
    user_id = message.chat.id
    params = users_params[user_id]
    conversation_default = dialogue.get_system(user_id)
    bot.send_message(user_id, f'Системное сообщение: {conversation_default["content"]}')
    bot.send_message(user_id, "Напишите системное сообщение боту, которое задаёт стиль общения.")
    params.mode = BotState.SYSTEM


@bot.message_handler(commands=["voice"])
def send_voice(message):
    user_id = message.chat.id
    params = users_params[user_id]
    speech = users_speech[user_id]
    url = "https://cloud.yandex.ru/ru/docs/speechkit/tts/voices"
    bot.send_message(user_id, f"Голос: {speech.voice}. Введите название голоса: {url}")
    params.mode = BotState.VOICE


@bot.message_handler(commands=["answer"])
def send_answer(message):
    user_id = message.chat.id
    params = users_params[user_id]
    answers = map(lambda arg: arg.capitalize(), get_class_values(BotAnswer))
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(*answers)
    bot.send_message(
        user_id, f"Формат: {params.answer}. Введите формат ответа: {', '.join(answers)}.", reply_markup=markup
    )
    params.mode = BotState.ANSWER


@bot.message_handler(commands=["echo"])
def send_echo(message):
    user_id = message.chat.id
    params = users_params[user_id]
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Эхобот", "Искусственный интеллект")
    bot.send_message(user_id, "Выберите режим функционирования бота.", reply_markup=markup)
    params.mode = BotState.ECHO


def check_message(user_id: str, user_input: str, choises: list[str]) -> bool:
    user_input = user_input.strip().lower()
    if user_input in map(lambda arg: arg.lower(), choises):
        return True
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(*choises)
    bot.send_message(user_id, "Неверный ответ. Попробуйте ещё...", reply_markup=markup)
    return False


@bot.message_handler(func=lambda message: True, content_types=["text", "voice"])
def handle_message(message):
    user_id = message.chat.id
    params = users_params[user_id]
    speech = users_speech[user_id]
    next_state = True
    markup = ReplyKeyboardRemove()

    if message.content_type == "voice":
        file_info = bot.get_file(message.voice.file_id)
        audio_data = bot.download_file(file_info.file_path)
        user_input = speech.recognize(audio_data).strip()
        if user_input:
            bot.send_message(message.chat.id, user_input, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "Извините, я не смог распознать ваше сообщение.", reply_markup=markup)
            return
    else:
        user_input = message.text

    if params.mode == BotState.SYSTEM:
        dialogue.system(user_id, user_input)
        markup = ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add("Да", "Нет")
        bot.send_message(user_id, "Сбросить ваш диалог?", reply_markup=markup)
        params.mode = BotState.SYSTEM_STEP2
        next_state = False

    elif params.mode == BotState.SYSTEM_STEP2:
        user_input = user_input.strip().capitalize()
        menu = {"Да": lambda: dialogue.clear(user_id), "Нет": lambda: dialogue.add_system(user_id)}
        if check_message(user_id, user_input, list(menu.keys())):
            menu[user_input]()
            bot.send_message(user_id, "Системное сообщение записал!", reply_markup=markup)
        else:
            next_state = False

    elif params.mode == BotState.ECHO:
        user_input = user_input.strip().capitalize()
        menu = {"Эхобот": BotEcho.ECHO, "Искусственный интеллект": BotEcho.AI}
        if check_message(user_id, user_input, list(menu.keys())):
            params.echo = menu[user_input]
            bot.send_message(user_id, "Режим изменил!", reply_markup=markup)
        else:
            next_state = False

    elif params.mode == BotState.VOICE:
        user_input = user_input.strip().lower()
        if is_value_in_class_values(user_input, SpeechVoice):
            speech.set_synthesis(user_input)
            bot.send_message(user_id, "Голос сохранил!", reply_markup=markup)
        else:
            bot.send_message(user_id, "Нет такого голоса, попробуйте ещё...", reply_markup=markup)
            next_state = False

    elif params.mode == BotState.ANSWER:
        user_input = user_input.strip().lower()
        if is_value_in_class_values(user_input, BotAnswer):
            params.answer = user_input
            bot.send_message(user_id, "Формат ответа сохранил!", reply_markup=markup)
        else:
            bot.send_message(user_id, "Нет такого значения, попробуйте ещё...", reply_markup=markup)
            next_state = False

    else:
        ai_response_content = dialogue.generate(user_id, user_input) if params.echo == BotEcho.AI else user_input
        if params.answer in (BotAnswer.VOICE, BotAnswer.ALL):
            audio_stream = speech.synthesize(ai_response_content)
            bot.send_voice(user_id, audio_stream)
        if params.answer in (BotAnswer.TEXT, BotAnswer.ALL):
            bot.send_message(user_id, ai_response_content, reply_markup=markup, parse_mode="Markdown")

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
            BotCommand("echo", "Режим эхобота"),
        ]
    )
    bot.infinity_polling()
