from typing import Optional


class BaseMainException(Exception):
    def __init__(self, message: Optional[str] = None):
        self.message = message

    def __str__(self):
        return self.message if self.message else "<None>"


class UnableDetectLanguage(BaseMainException):
    def __init__(self):
        self.message = "Unable to detect language"


class UnidentifiedMode(BaseMainException):
    def __init__(self):
        self.message = "Unidentified bot operating mode"


class NotFoundHandler(BaseMainException):
    def __init__(self, state):
        self.message = f"No handler found for state {state}"
