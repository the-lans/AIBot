from io import BytesIO
import logging
from typing import Optional, Union

from gtts import gTTS
from speechkit import configure_credentials, creds, model_repository
from speechkit.stt import AudioProcessingType

from lib.config import Config
from lib.enum import BaseEnum


logger = logging.getLogger(__name__)
configure_credentials(yandex_credentials=creds.YandexCredentials(api_key=Config.API_KEY_YANDEX_TTS))


class SpeechVoice(BaseEnum):
    GOOGLE = "google"
    JOHN = "john"
    LEA = "lea"
    NAOMI = "naomi"
    AMIRA = "amira"
    MADI = "madi"
    ALENA = "alena"
    FILIPP = "filipp"
    ERMIL = "ermil"
    JANE = "jane"
    MADIRUS = "madirus"
    OMAZH = "omazh"
    ZAHAR = "zahar"
    DASHA = "dasha"
    JULIA = "julia"
    LERA = "lera"
    MASHA = "masha"
    MARINA = "marina"
    ALEXANDER = "alexander"
    KIRILL = "kirill"
    ANTON = "anton"
    NIGORA = "nigora"


class SpeechLang(BaseEnum):
    AUTO = "auto"  # Авто
    DE = "de-DE"  # Немецкий
    US = "en-US"  # Английский
    ES = "es-ES"  # Испанский
    FI = "fi-FI"  # Финский
    FR = "fr-FR"  # Французский
    HE = "he-HE"  # Иврит
    IT = "it-IT"  # Итальянский
    KZ = "kk-KZ"  # Казахский
    NL = "nl-NL"  # Голландский
    PL = "pl-PL"  # Польский
    PT = "pt-PT"  # Португальский
    BR = "pt-BR"  # Бразильский португальский
    RU = "ru-RU"  # Русский язык
    SE = "sv-SE"  # Шведский
    TR = "tr-TR"  # Турецкий
    UZ = "uz-UZ"  # Узбекский (латиница)


class Speech:
    def __init__(self, voice: str, lang: str = "auto"):
        self.audio_stream = BytesIO()
        self.voice = voice
        self.lang = lang
        self.model_synthesis = None
        self.model_recognition = None
        self.set_synthesis(voice)
        self.set_recognition(lang)

    def __deepcopy__(self, memo):
        new_obj = Speech(self.voice, self.lang)
        memo[id(self)] = new_obj
        return new_obj

    def init(self, data: dict):
        voice = data.get("voice")
        lang = data.get("lang")
        if voice:
            self.voice = voice
            self.set_synthesis(voice)
        if lang:
            self.lang = lang
            self.set_recognition(lang)

    def to_dict(self) -> dict:
        fields_to_include = ["voice", "lang"]
        return {key: value for key, value in vars(self).items() if key in fields_to_include}

    @property
    def lang2(self):
        return self.lang if self.lang == "auto" else self.lang[:2]

    def is_google(self) -> bool:
        return self.voice == SpeechVoice.GOOGLE

    def set_synthesis(self, voice: str):
        self.voice = voice
        if not self.is_google():
            if self.model_synthesis is None:
                self.model_synthesis = model_repository.synthesis_model()
            self.model_synthesis.voice = voice
            # self.model_synthesis.role = "neutral"

    def set_recognition(self, lang: str = "auto"):
        self.lang = lang
        if self.model_recognition is None:
            self.model_recognition = model_repository.recognition_model()
        self.model_recognition.model = "general"
        self.model_recognition.language = lang
        self.model_recognition.audio_processing_type = AudioProcessingType.Full

    def synthesize(self, text: str) -> BytesIO:
        self.audio_stream = BytesIO()
        if not self.is_google():
            result = self.model_synthesis.synthesize(text, raw_format=False)
            result.export(self.audio_stream, format="wav")
        else:
            tts = gTTS(text, lang=self.lang2)
            tts.write_to_fp(self.audio_stream)
        self.audio_stream.seek(0)
        return self.audio_stream

    @staticmethod
    def _recognize_log(result: list, detail: bool = False) -> str:
        lines = []
        for c, res in enumerate(result):
            normalized_text = res.normalized_text.replace("\n", " ")
            utterances = None
            if res.has_utterances():
                utterances = [str(utterance).replace("\n", " ") for utterance in res.utterances]
            if detail:
                raw_text = res.raw_text.replace("\n", " ")
                lines += [f"channel: {c}", f"raw_text: {raw_text}", f"norm_text: {normalized_text}"]
                if utterances:
                    lines += [f"utterances: {' '.join(utterances)}"]
            else:
                lines += [f"channel: {c}", " ".join(utterances) if utterances else normalized_text]
        return "\n".join(lines) if detail else " ".join(lines)

    def recognize(self, audio_bytes: bytes) -> str:
        result = self.model_recognition.transcribe(audio_bytes)
        logger.info("Recognize text: %s", self._recognize_log(result))
        text = "\n".join([res.normalized_text for res in result])
        return text

    @staticmethod
    def choce_from_lang(lst: Union[tuple, list], lang: str) -> Optional["Speech"]:
        def _get_item(lst, value, split):
            for item in lst:
                if item.lang[:split] == value:
                    return item
            return None

        if lang != "auto":
            if result := _get_item(lst, lang, 5):
                return result
            if result := _get_item(lst, lang, 2):
                return result
        if result := _get_item(lst, "auto", 5):
            return result
        return None

    @staticmethod
    def get_langs(lst: Union[tuple, list]) -> list[str]:
        return [item.lang for item in lst]

    @staticmethod
    def get_langs2(lst: Union[tuple, list]) -> list[str]:
        return [item.lang2 for item in lst]
