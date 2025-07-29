import json
import os

DEFAULT_SETTINGS = {
    "excluded_keywords": [],
    "included_keywords": [],
    "days_limit": 3
}

class FilterSettings:
    def __init__(self, filepath="data/filter_settings.json"):
        self.filepath = filepath
        self.settings = DEFAULT_SETTINGS.copy()
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
            except Exception:
                pass

    def save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def get(self):
        return self.settings

    def update_keywords(self, key, words):
        self.settings[key] = words
        self.save()

    def set_days_limit(self, days):
        self.settings["days_limit"] = days
        self.save()
