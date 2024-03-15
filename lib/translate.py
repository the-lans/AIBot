from typing import Optional

import requests

from lib.config import Config


class Translate:
    def __init__(self, folder_id: Optional[str] = None):
        self.folder_id = folder_id
        self.language_code_hints = []

    def set_language(self, langs: list[str]):
        self.language_code_hints = []
        for item in langs:
            if item == "auto":
                self.language_code_hints = []
                break
            self.language_code_hints.append(item[:2])

    def detect_language(self, text: str) -> Optional[str]:
        url = "https://translate.api.cloud.yandex.net/translate/v2/detect"
        headers = {"Authorization": f"Api-Key {Config.API_KEY_YANDEX_TTS}", "Content-Type": "application/json"}
        data = {"text": text}
        if self.folder_id:
            data["folderId"] = self.folder_id
        if self.language_code_hints:
            data["language_code_hints"] = self.language_code_hints
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            language = response.json()["languageCode"]
            return language
        else:
            return None
