from collections import defaultdict
from datetime import datetime
import logging
from typing import Optional

from telebot.types import BotCommand, ReplyKeyboardMarkup

from lib.bot_params import BotAIModel, BotAnswer, BotMode, BotParams, BotState, get_class_dict
from lib.config import Config
from lib.helpers import (
    StateHandlerDecorator,
    admin_required,
    bot,
    check_message,
    check_start_user,
    check_user_access,
    command_with_timeout,
    cut_long_message,
    hide_markup,
    is_message_chain,
    parse_args,
    send_message_admin,
    user_storage,
)
from lib.openai import DialogueAI
from lib.speech import Speech, SpeechLang, SpeechVoice
from lib.translate import Translate


SPEECH_MENU = (SpeechLang.AUTO, SpeechLang.RU, SpeechLang.US)

logger = logging.getLogger(__name__)
dialogue = DialogueAI(Config.OPENAI_MODEL)
users_params = defaultdict(lambda: BotParams())
users_speech = defaultdict(lambda: (Speech("marina", "auto"), Speech("john", "en-US")))
trans = Translate()
state_handler = StateHandlerDecorator()


@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    dialogue.system(user_id)
    dialogue.clear(user_id)
    users_params[user_id] = BotParams()
    msg = [
        "Привет! Я многофункциональный бот. Вот то, что я умею:",
        " * Вести диалог на любую тему: /model -> GPT-4 Turbo 128K",
        " * Превращать ваш голос в текст",
        " * Читать текст выбранным голосом: /lang",
        " * Рисовать картинки по запросу: /model -> DALL-E 3",
    ]
    bot.send_message(user_id, "\n".join(msg), reply_markup=hide_markup)


@bot.message_handler(commands=["users"])
@admin_required
def send_users(message):
    user_id = message.chat.id
    users_str = user_storage.to_str()
    bot.send_message(user_id, f"Информация пользователей:\n" + users_str, reply_markup=hide_markup)


@bot.message_handler(commands=["allow_access"])
@admin_required
@parse_args(r"/allow_access (\d+)")
def send_allow_access(message, from_user_id):
    user_storage.add_user(from_user_id, {"access": True})
    send_message_admin(f"Доступ разрешён для пользователя с ID: {from_user_id}.")


@bot.message_handler(commands=["ban_access"])
@admin_required
@parse_args(r"/ban_access (\d+)")
def send_ban_access(message, from_user_id):
    user_storage.add_user(from_user_id, {"access": False})
    send_message_admin(f"Доступ запрещён для пользователя с ID: {from_user_id}.")


@bot.message_handler(commands=["clear"])
def send_clear(message):
    user_id = message.chat.id
    params = users_params[user_id]
    dialogue.clear(user_id)
    bot.send_message(user_id, "Очистил ваш диалог.", reply_markup=hide_markup)
    params.state = BotState.CLEAR


@bot.message_handler(commands=["system"])
def send_system(message):
    user_id = message.chat.id
    params = users_params[user_id]
    conversation_default = dialogue.get_system(user_id)
    bot.send_message(user_id, f'Системное сообщение: {conversation_default["content"]}', reply_markup=hide_markup)
    bot.send_message(
        user_id, "Напишите системное сообщение боту, которое задаёт стиль общения.", reply_markup=hide_markup
    )
    params.state = BotState.SYSTEM


@state_handler.add_handler(BotState.SYSTEM)
def handle_system(user_id: str, user_input: str) -> Optional[bool]:
    params = users_params[user_id]
    dialogue.system(user_id, user_input)
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Да", "Нет")
    bot.send_message(user_id, "Сбросить ваш диалог?", reply_markup=markup)
    params.state = BotState.SYSTEM_STEP2
    return False


@state_handler.add_handler(BotState.SYSTEM_STEP2)
def handle_system_step2(user_id: str, user_input: str) -> Optional[bool]:
    menu = {"Да": lambda: dialogue.clear(user_id), "Нет": lambda: dialogue.add_system(user_id)}
    if check_message(bot, user_id, user_input, list(menu.keys())):
        menu[user_input]()
        bot.send_message(user_id, "Системное сообщение записал!", reply_markup=hide_markup)
    else:
        return False


@bot.message_handler(commands=["lang"])
def send_lang(message):
    user_id = message.chat.id
    params = users_params[user_id]
    speech = users_speech[user_id][0]
    markup_menu = [item[0] for item in SPEECH_MENU]
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(*markup_menu)
    url = "https://cloud.yandex.ru/ru/docs/speechkit/stt/models"
    msg = [
        f"Язык: {speech.lang}. Выберите первый язык бота.",
        f"Список языков здесь: {url}",
        "Кроме этого, можно указать автоматическое распознавание языка 'auto'.",
    ]
    bot.send_message(user_id, "\n".join(msg), reply_markup=markup)
    params.state = BotState.RECOGNITION


def choice_recognition(user_id: str, user_input: str, step: int) -> Optional[bool]:
    params = users_params[user_id]
    speech = users_speech[user_id][step - 1]
    menu = get_class_dict(SpeechLang)
    markup_menu = [item[0] for item in SPEECH_MENU]
    msg_error = "Нет такого языка, попробуйте ещё..."
    if check_message(bot, user_id, user_input, list(menu.keys()), is_markup=markup_menu, msg_error=msg_error):
        speech.set_recognition(user_input)
        bot.send_message(user_id, "Язык сохранил!", reply_markup=hide_markup)
        if step == 1:
            url = "https://cloud.yandex.ru/ru/docs/speechkit/tts/voices"
            msg = [
                f"Голос: {speech.voice}. Введите название первого голоса.",
                f"Список голосов здесь: {url}",
                f"Кроме этого, есть голос с названием 'google'.",
            ]
            bot.send_message(user_id, "\n".join(msg), reply_markup=hide_markup)
            params.state = BotState.VOICE
            return False
        elif step == 2:
            bot.send_message(
                user_id, f"Голос: {speech.voice}. Введите название второго голоса.", reply_markup=hide_markup
            )
            params.state = BotState.VOICE_STEP2
            return False
    else:
        return False


@state_handler.add_handler(BotState.RECOGNITION)
def handle_recognition(user_id: str, user_input: str) -> Optional[bool]:
    return choice_recognition(user_id, user_input, 1)


@state_handler.add_handler(BotState.RECOGNITION_STEP2)
def handle_recognition2(user_id: str, user_input: str) -> Optional[bool]:
    return choice_recognition(user_id, user_input, 2)


def choice_voice(user_id: str, user_input: str, step: int) -> Optional[bool]:
    params = users_params[user_id]
    speech = users_speech[user_id][step - 1]
    menu = get_class_dict(SpeechVoice)
    msg_error = "Нет такого голоса, попробуйте ещё..."
    if check_message(bot, user_id, user_input, list(menu.keys()), is_markup=False, msg_error=msg_error):
        speech.set_synthesis(user_input)
        bot.send_message(user_id, "Голос сохранил!", reply_markup=hide_markup)
        if step == 1:
            speech = users_speech[user_id][step]
            markup_menu = [item[0] for item in SPEECH_MENU]
            markup = ReplyKeyboardMarkup(one_time_keyboard=True)
            markup.add(*markup_menu)
            bot.send_message(user_id, f"Язык: {speech.lang}. Выберите второй язык бота.", reply_markup=markup)
            params.state = BotState.RECOGNITION_STEP2
            return False
        elif step == 2:
            return True
    else:
        return False


@state_handler.add_handler(BotState.VOICE)
def handle_voice(user_id: str, user_input: str) -> Optional[bool]:
    return choice_voice(user_id, user_input, 1)


@state_handler.add_handler(BotState.VOICE_STEP2)
def handle_voice2(user_id: str, user_input: str) -> Optional[bool]:
    return choice_voice(user_id, user_input, 2)


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
    params.state = BotState.ANSWER


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
    params.state = BotState.MODEL


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


@bot.message_handler(commands=["mode"])
def send_mode(message):
    user_id = message.chat.id
    params = users_params[user_id]
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Эхобот", "Искусственный интеллект")
    bot.send_message(user_id, "Выберите режим функционирования бота.", reply_markup=markup)
    params.state = BotState.MODE


@state_handler.add_handler(BotState.MODE)
def handle_mode(user_id: str, user_input: str) -> Optional[bool]:
    params = users_params[user_id]
    menu = get_class_dict(BotMode)
    if check_message(bot, user_id, user_input, list(menu.keys())):
        params.mode = menu[user_input]
        bot.send_message(user_id, "Режим изменил!", reply_markup=hide_markup)
    else:
        return False


@state_handler.add_handler(None)
def handle_output_message(user_id: str, user_input: str) -> Optional[bool]:
    params = users_params[user_id]
    image_bytes = None

    if check_user_access(user_id):
        if params.mode == BotMode.AI:
            bot.send_message(
                user_id, f"Ваш запрос отправлен для генерации в {params.model[0]}", reply_markup=hide_markup
            )
            response_content, image_bytes = dialogue.generate(user_id, user_input)
        elif params.mode == BotMode.ECHO:
            response_content = user_input
        else:
            raise Exception("Unidentified bot operating mode")
    else:
        bot.send_message(user_id, "Число генераций для вас ограничено администратором!", reply_markup=hide_markup)
        return None

    if image_bytes:
        bot.send_photo(user_id, image_bytes)

    response_content = cut_long_message(response_content, 4000)
    logger.info("User: %s, Output: %s", user_id, response_content)
    if params.answer in (BotAnswer.VOICE, BotAnswer.ALL):
        trans.set_language(Speech.get_langs(users_speech[user_id]))
        lang = trans.detect_language(response_content)
        speech = Speech.choce_from_lang(users_speech[user_id], lang) if lang else users_speech[user_id][0]
        audio_stream = speech.synthesize(response_content)
        bot.send_voice(user_id, audio_stream)
    if params.answer in (BotAnswer.TEXT, BotAnswer.ALL):
        bot.send_message(user_id, response_content, parse_mode="Markdown", reply_markup=hide_markup)
    return None


def handle_input_message(message) -> (Optional[str], str):
    user_id = message.chat.id
    params = users_params[user_id]
    message_time = datetime.fromtimestamp(message.date)
    params.data["last_time"] = message_time
    content_type = message.content_type
    if content_type == "voice":
        speech = Speech.choce_from_lang(users_speech[user_id], "auto")
        if speech is None:
            speech = users_speech[user_id][0]
        params.data["file_id"] = None
        file_info = bot.get_file(message.voice.file_id)
        audio_data = bot.download_file(file_info.file_path)
        user_input = speech.recognize(audio_data).strip()
        if user_input:
            bot.send_message(message.chat.id, user_input, parse_mode="Markdown", reply_markup=hide_markup)
        else:
            bot.send_message(
                message.chat.id, "Извините, я не смог распознать ваше сообщение.", reply_markup=hide_markup
            )
            return None, content_type
    else:
        user_input = message.text
        logger.info("User: %s, Content type: %s, Input: %s", user_id, content_type, user_input)
        if is_message_chain(message):
            params.data["text"] += user_input
            content_type = "chain"
        else:
            user_input = params.data["text"] + user_input
            params.data["text"] = ""
    return user_input, content_type


@bot.message_handler(func=lambda message: True, content_types=["text", "voice"])
@command_with_timeout(timeout=180)
def handle_message(message):
    user_id = message.chat.id
    params = users_params[user_id]
    next_state = True

    # Распознавание входящего сообщения
    user_input, content_type = handle_input_message(message)
    if user_input is None or content_type == "chain":
        return

    # Управление пользователями
    check_start_user(message)

    # Функционал в зависимости от состояния
    result = state_handler.handle(params.state, user_id, user_input)
    if result is not None:
        next_state = result
    if next_state:
        params.state = BotState.MESSAGE


if __name__ == "__main__":
    file_handler = logging.FileHandler("app.log")
    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[file_handler, stream_handler],
    )

    bot.set_my_commands(
        [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("clear", "Очистить ваш диалог"),
            BotCommand("system", "Изменить стиль общения"),
            BotCommand("lang", "Задать язык и голос"),
            BotCommand("answer", "Формат ответа: текст или аудио"),
            BotCommand("model", "Выбор модели ИИ"),
            BotCommand("mode", "Выбор режима: эхобот или ИИ"),
        ]
    )
    bot.infinity_polling()
