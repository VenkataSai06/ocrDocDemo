from __future__ import annotations

import re
from typing import Any, Dict, List

from .extractors import (
    clean_ocr_text,
    extract_additives,
    extract_allergens,
    extract_ingredients,
    extract_metadata,
    extract_nutrition,
)
from .normalization import FoodNormalizationService


class FoodExtractionService:
    def __init__(self):
        self.normalizer = FoodNormalizationService()

    def process(self, ocr_output: Dict[str, Any]) -> Dict[str, Any]:
        raw_text = ocr_output.get("raw_text") or ""
        cleaned_text = clean_ocr_text(raw_text)
        product = {
            "document_id": ocr_output.get("document_id"),
            "product": extract_metadata(cleaned_text),
            "ingredients": extract_ingredients(raw_text),
            "nutrition": {
                "serving_size": {"value": None, "unit": None},
                "servings_per_container": None,
                "energy_kcal": None,
                "protein_g": None,
                "carbohydrates_g": None,
                "total_sugars_g": None,
                "added_sugars_g": None,
                "fat_g": None,
                "saturated_fat_g": None,
                "trans_fat_g": None,
                "fiber_g": None,
                "sodium_mg": None,
            },
            "additives": extract_additives(raw_text),
            "allergens": extract_allergens(raw_text),
            "source": {
                "raw_ocr_text": raw_text,
                "cleaned_ocr_text": cleaned_text,
            },
        }
        nutrition = extract_nutrition(raw_text)
        product["nutrition"].update(nutrition)
        return product


class FoodValidationService:
    def __init__(self):
        pass

    def process(self, normalized_product: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[str] = []
        source_text = normalized_product.get("source", {}).get("raw_ocr_text") or ""

        for ingredient in normalized_product.get("ingredients", []):
            raw = ingredient.get("raw") or ""
            if not raw or raw.strip() == "":
                issues.append("Empty ingredient detected.")
            if ingredient.get("status") == "needs_review":
                issues.append(f"Ingredient needs review: {raw}")

        nutrition = normalized_product.get("nutrition", {})
        for key, value in nutrition.items():
            if isinstance(value, (int, float)) and value < 0:
                issues.append(f"Negative nutrition value for {key}: {value}")

        negative_patterns = re.findall(r"([A-Za-z\s]+?)\s*[-:]?\s*(-\d+(?:\.\d+)?)\s*(g|mg|kcal|kj)", source_text, flags=re.I)
        for label, number, unit in negative_patterns:
            issues.append(f"Negative nutrition value for {label.strip()}: {number}{unit}")

        for additive in normalized_product.get("additives", []):
            code = additive.get("code") or ""
            if code and not re.fullmatch(r"\d{3,4}", str(code)):
                issues.append(f"Invalid additive code: {code}")

        status = "valid" if not issues else "needs_review"
        normalized_product["validation"] = {"status": status, "issues": issues}
        return normalized_product
