from io import BytesIO
import logging

from gtts import gTTS
from speechkit import configure_credentials, creds, model_repository
from speechkit.stt import AudioProcessingType

from lib.config import Config


logger = logging.getLogger(__name__)
configure_credentials(yandex_credentials=creds.YandexCredentials(api_key=Config.API_KEY_YANDEX_TTS))


class SpeechVoice:
    GOOGLE = "google"
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


class SpeechLang:
    DE = ("de-DE", "Немецкий")
    US = ("en-US", "Английский")
    ES = ("es-ES", "Испанский")
    FI = ("fi-FI", "Финский")
    FR = ("fr-FR", "Французский")
    HE = ("he-HE", "Иврит")
    IT = ("it-IT", "Итальянский")
    KZ = ("kk-KZ", "Казахский")
    NL = ("nl-NL", "Голландский")
    PL = ("pl-PL", "Польский")
    PT = ("pt-PT", "Португальский")
    BR = ("pt-BR", "Бразильский португальский")
    RU = ("ru-RU", "Русский язык (по умолчанию)")
    SE = ("sv-SE", "Шведский")
    TR = ("tr-TR", "Турецкий")
    UZ = ("uz-UZ", "Узбекский (латиница)")


class Speech:
    def __init__(self, voice: str, lang: str = "auto"):
        self.audio_stream = BytesIO()
        self.voice = voice
        self.model_synthesis = None
        self.model_recognition = None
        self.set_synthesis(voice)
        self.set_recognition(lang)

    def set_synthesis(self, voice: str):
        self.voice = voice
        self.model_synthesis = None
        if voice != SpeechVoice.GOOGLE:
            self.model_synthesis = model_repository.synthesis_model()
            self.model_synthesis.voice = voice
            # self.model_synthesis.role = "neutral"

    def set_recognition(self, lang: str = "auto"):
        self.model_recognition = model_repository.recognition_model()
        self.model_recognition.model = "general"
        self.model_recognition.language = lang
        self.model_recognition.audio_processing_type = AudioProcessingType.Full

    def synthesize(self, text: str) -> BytesIO:
        self.audio_stream = BytesIO()
        if self.model_synthesis:
            result = self.model_synthesis.synthesize(text, raw_format=False)
            result.export(self.audio_stream, format="wav")
        else:
            tts = gTTS(text, lang="ru")
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
