import yaml


class Config:
    API_KEY_OPENAI = None
    OPENAI_URL = None
    API_KEY_YANDEX_TTS = None
    API_KEY_TELEGRAM_BOT = None
    OPENAI_MODEL = "gpt-3.5-turbo-1106"
    ADMIN_IDS = []

    @classmethod
    def load_config(cls, file_path="config.yaml"):
        with open(file_path, "r") as file:
            config_data = yaml.safe_load(file)
            cls.API_KEY_OPENAI = config_data["API_KEY_OPENAI"]
            cls.OPENAI_URL = config_data["OPENAI_URL"]
            cls.OPENAI_MODEL = config_data["OPENAI_MODEL"]
            cls.API_KEY_YANDEX_TTS = config_data["API_KEY_YANDEX_TTS"]
            cls.API_KEY_TELEGRAM_BOT = config_data["API_KEY_TELEGRAM_BOT"]
            cls.ADMIN_IDS = config_data["ADMIN_IDS"]


# Загрузка конфигурации
Config.load_config()
