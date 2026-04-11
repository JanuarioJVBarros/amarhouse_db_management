import os
import hashlib


class FileCache:

    def __init__(self, folder="cache"):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def get_path(self, url: str) -> str:
        return os.path.join(self.folder, self._key(url) + ".html")

    def has(self, url: str) -> bool:
        return os.path.exists(self.get_path(url))

    def save(self, url: str, content: str):
        with open(self.get_path(url), "w", encoding="utf-8") as f:
            f.write(content)

    def load(self, url: str) -> str:
        try:
            with open(self.get_path(url), "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return None