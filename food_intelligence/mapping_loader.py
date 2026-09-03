from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


class MappingLoader:
    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent / "mappings"
        self.base_dir = Path(base_dir)

    def load_json(self, filename: str) -> Dict[str, Any]:
        path = self.base_dir / filename
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @property
    def ingredients(self) -> Dict[str, str]:
        return self.load_json("ingredients.json")

    @property
    def additives(self) -> Dict[str, Any]:
        return self.load_json("additives.json")

    @property
    def synonyms(self) -> Dict[str, str]:
        return self.load_json("synonyms.json")
