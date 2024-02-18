from typing import Optional

from openai import OpenAI

from lib.config import Config


class DialogueAI:
    def __init__(self, model: str = "gpt-3.5-turbo-1106"):
        self.openai_client = OpenAI(api_key=Config.API_KEY_OPENAI, base_url=Config.OPENAI_URL)
        self.model = model
        # Словарь для хранения истории разговора с каждым пользователем
        self.conversation_histories = {}
        self.conversation_default = {}

    def system(self, user_id: str, system_text: Optional[str] = None):
        if system_text is None:
            system_text = "Ты — ChatGPT, большая языковая модель, обученная OpenAI. "
            system_text += "Внимательно следуй инструкциям пользователя. "
            system_text += "Ты отвечаешь пользователю в Telegram, используй Markdown."
        self.conversation_default[user_id] = {"role": "system", "content": system_text}

    def get_system(self, user_id: str):
        if user_id not in self.conversation_default:
            self.system(user_id)
        return self.conversation_default[user_id]

    def clear(self, user_id: str):
        self.conversation_histories[user_id] = [self.get_system(user_id)]

    def add_message(self, user_id: str, role: str, content: str):
        if user_id not in self.conversation_histories:
            self.clear(user_id)
        conversation_history = self.conversation_histories[user_id]
        conversation_history.append({"role": role, "content": content})

    def add_system(self, user_id: str):
        message = self.get_system(user_id)
        self.add_message(user_id, "system", message["content"])

    def generate(self, user_id: str, user_input: str):
        self.add_message(user_id, "user", user_input)
        conversation_history = self.conversation_histories[user_id]
        chat_completion = self.openai_client.chat.completions.create(model=self.model, messages=conversation_history)
        ai_response_content = chat_completion.choices[0].message.content
        return ai_response_content