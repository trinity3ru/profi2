import json
import os

class ProcessedOrderStorage:
    def __init__(self, filepath="data/processed_orders.json"):
        self.filepath = filepath
        self.orders = set()
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.orders = set(json.load(f))
            except Exception:
                self.orders = set()

    def add(self, order_id: str):
        self.orders.add(order_id)
        self._save()

    def contains(self, order_id: str) -> bool:
        return order_id in self.orders

    def _save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(list(self.orders), f, ensure_ascii=False, indent=2)
