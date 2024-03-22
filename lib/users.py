import copy
from datetime import datetime
import json
from typing import Any, Dict, Union


# Конвертирует объект в строку
def object_to_json(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, "to_json") and callable(getattr(obj, "to_json")):
        return obj.to_json()
    elif isinstance(obj, (dict, list, tuple, str, int, float, bool, type(None))):
        return obj
    else:
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


# Функция для обработки объектов в процессе загрузки JSON
def json_to_object_hook(json_dict: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in json_dict.items():
        if isinstance(value, str):
            try:
                json_dict[key] = datetime.fromisoformat(value)
            except Exception:
                pass
    return json_dict


class UserStorage:
    def __init__(self, file_path: str):
        self.file_path: str = file_path
        self.users: dict = self._load_users_from_file()

    def to_str(self):
        res = []
        for user_id, additional_params in self.users.items():
            res.append(f"{user_id}: {additional_params}")
        return "  \n".join(res)

    def _load_users_from_file(self) -> dict:
        try:
            with open(self.file_path, "r") as file:
                return json.load(file, object_hook=json_to_object_hook)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_users_to_file(self) -> None:
        with open(self.file_path, "w") as file:
            json.dump(self.users, file, indent=4, default=object_to_json)

    def add_user(self, user_id: Union[int, str], additional_params: dict = None, save: bool = True) -> None:
        user_id = str(user_id)
        additional_params = additional_params or {}
        if user_id in self.users:
            self.users[user_id].update(additional_params)
        else:
            self.users[user_id] = additional_params
        if save:
            self._save_users_to_file()

    def get_user(self, user_id: Union[int, str]) -> dict:
        user_id = str(user_id)
        return self.users.get(user_id, {})

    def has_user(self, user_id: Union[int, str]) -> bool:
        user_id = str(user_id)
        return user_id in self.users

    def remove_user(self, user_id: int) -> None:
        user_id = str(user_id)
        if user_id in self.users:
            del self.users[user_id]
            self._save_users_to_file()

    def set_params(self, name: str, data: dict) -> None:
        for user_id, obj in data.items():
            self.add_user(user_id, {name: obj.to_dict()}, False)

    def set_params_tuple(self, names: tuple, data: dict) -> None:
        for user_id, obj in data.items():
            for idx, item in enumerate(obj):
                self.add_user(user_id, {names[idx]: item.to_dict()}, False)

    def set_object(self, name: str, obj: Any) -> None:
        for user_id, val in obj.to_dict().items():
            self.add_user(user_id, {name: val}, False)

    def get_params(self, name: str, obj_default: Any) -> dict:
        data = {}
        for user_id, obj in self.users.items():
            if name in obj:
                obj_new = copy.deepcopy(obj_default)
                obj_new.init(obj[name])
                data[user_id] = obj_new
        return data

    def get_params_tuple(self, names: tuple, tuple_default: tuple) -> dict:
        data = {}
        for user_id, obj in self.users.items():
            tuple_new = copy.deepcopy(tuple_default)
            for idx, item in enumerate(tuple_new):
                name = names[idx]
                if name in obj:
                    item.init(obj[name])
            data[user_id] = tuple_new
        return data

    def get_object(self, name: str, obj: Any) -> None:
        data = {}
        for user_id, val in self.users.items():
            if name in val:
                data[user_id] = val[name]
        obj.init(data)

    def save_external(self, users_params: dict, users_speech: dict, dialogue: Any) -> None:
        self.set_params("params", users_params)
        self.set_params_tuple(("speech_1", "speech_2"), users_speech)
        self.set_object("dialogue", dialogue)
        self._save_users_to_file()


# Example usage:
"""
user_storage = UserStorage("users.json")
user_storage.add_user(user_id=123456, additional_params={"access_granted": True}, True)
user_info = user_storage.get_user(user_id=123456)
print(user_info)  # Output: {'access_granted': True}
"""
