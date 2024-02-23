import json
from typing import Union


class UserStorage:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.users = self._load_users_from_file()

    def to_str(self):
        res = []
        for user_id, additional_params in self.users.items():
            res.append(f"{user_id}: {additional_params}")
        return "  \n".join(res)

    def _load_users_from_file(self) -> dict:
        try:
            with open(self.file_path, "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_users_to_file(self) -> None:
        with open(self.file_path, "w") as file:
            json.dump(self.users, file, indent=4)

    def add_user(self, user_id: Union[int, str], additional_params: dict = None) -> None:
        user_id = str(user_id)
        additional_params = additional_params or {}
        if user_id in self.users:
            self.users[user_id].update(additional_params)
        else:
            self.users[user_id] = additional_params
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


# Example usage:
"""
user_storage = UserStorage("users.json")
user_storage.add_user(user_id=123456, additional_params={"access_granted": True})
user_info = user_storage.get_user(user_id=123456)
print(user_info)  # Output: {'access_granted': True}
"""
