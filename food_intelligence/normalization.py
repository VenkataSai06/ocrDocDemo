from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List

from .mapping_loader import MappingLoader


class FoodNormalizationService:
    def __init__(self):
        self.loader = MappingLoader()
        self.ingredients_map = self.loader.ingredients
        self.additives_map = self.loader.additives
        self.synonyms_map = self.loader.synonyms

    def _normalize_text(self, value: str) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKC", value)
        normalized = normalized.lower().replace("–", "-").replace("—", "-")
        normalized = re.sub(r"[^a-z0-9\s\-]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _resolve_ingredient(self, raw: str) -> Dict[str, Any]:
        key = self._normalize_text(raw)
        if not key:
            return {"canonical": None, "status": "unknown"}

        if key in self.ingredients_map:
            return {"canonical": self.ingredients_map[key], "status": "matched"}
        if key in self.synonyms_map:
            return {"canonical": self.synonyms_map[key], "status": "synonym_match"}

        return {"canonical": None, "status": "needs_review"}

    def _resolve_additive(self, raw_code: str) -> Dict[str, Any]:
        if not raw_code:
            return {"canonical_name": None, "status": "unknown"}
        cleaned = re.sub(r"[^0-9]", "", raw_code)
        if cleaned in self.additives_map:
            record = self.additives_map[cleaned]
            return {
                "canonical_name": record.get("canonical_name"),
                "status": "additive_match",
            }
        return {"canonical_name": None, "status": "needs_review"}

    def process(self, product: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {
            "document_id": product.get("document_id"),
            "product": product.get("product", {"name": None, "brand": None, "net_quantity": {"value": None, "unit": None}}),
            "ingredients": [],
            "nutrition": product.get("nutrition", {}),
            "additives": [],
            "allergens": product.get("allergens", {"contains": [], "may_contain": []}),
            "source": product.get("source", {"raw_ocr_text": None, "cleaned_ocr_text": None}),
            "validation": {"status": "valid", "issues": []},
            "traceability": {"raw_ocr_available": bool(product.get("source", {}).get("raw_ocr_text"))},
        }

        for item in product.get("ingredients", []):
            raw = item.get("raw")
            resolved = self._resolve_ingredient(raw or "")
            normalized_item = {
                "raw": raw,
                "canonical": resolved.get("canonical"),
                "status": resolved.get("status", "unknown"),
            }
            if item.get("codes"):
                code = item["codes"][0]
                if re.match(r"^(?:INS|E)\s*[- ]?\d{3,4}$", code, flags=re.I):
                    additive = self._resolve_additive(code)
                    normalized_item["canonical"] = additive.get("canonical_name") or normalized_item["canonical"]
                    normalized_item["status"] = additive.get("status", normalized_item["status"])
                    normalized_item["code"] = code
            normalized["ingredients"].append(normalized_item)

        for item in product.get("additives", []):
            raw_code = item.get("raw_code")
            code = item.get("code")
            additive = self._resolve_additive(raw_code or code or "")
            normalized["additives"].append({
                "raw_code": raw_code,
                "code": code,
                "system": item.get("system"),
                "canonical_name": additive.get("canonical_name"),
                "status": additive.get("status", "unknown"),
            })

        if not normalized["additives"]:
            for item in product.get("ingredients", []):
                codes = item.get("codes") or []
                for code in codes:
                    additive = self._resolve_additive(code)
                    normalized["additives"].append({
                        "raw_code": code,
                        "code": re.sub(r"[^0-9]", "", code),
                        "system": "INS" if re.match(r"^INS", code, flags=re.I) else "E",
                        "canonical_name": additive.get("canonical_name"),
                        "status": additive.get("status", "unknown"),
                    })

        return normalized
