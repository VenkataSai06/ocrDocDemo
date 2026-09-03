from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional


def clean_ocr_text(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = cleaned.replace("\r", "\n")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s*([:,;])\s*", r"\1 ", cleaned)
    cleaned = re.sub(r"\s*\(\s*", " (", cleaned)
    cleaned = re.sub(r"\s*\)\s*", ") ", cleaned)
    cleaned = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", cleaned)
    cleaned = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\bIN S\b", "INS", cleaned, flags=re.I)
    return cleaned


def normalize_key(value: Optional[str]) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.lower().replace("–", "-").replace("—", "-")
    normalized = re.sub(r"[^a-z0-9\s\-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def split_ingredient_text(raw_text: str) -> List[str]:
    text = raw_text.strip()
    if not text:
        return []
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            token = "".join(current).strip()
            if token:
                parts.append(token)
            current = []
            continue
        if char == ";" and depth == 0:
            token = "".join(current).strip()
            if token:
                parts.append(token)
            current = []
            continue
        current.append(char)
    final = "".join(current).strip()
    if final:
        parts.append(final)
    return [p.strip() for p in parts if p and p.strip()]


def extract_ingredient_name(raw_value: str) -> tuple[str, List[str]]:
    ingredient = raw_value.strip()
    if not ingredient:
        return "", []
    matches = re.findall(r"(?:INS|E)\s*[- ]?\d{3,4}", ingredient, flags=re.I)
    codes = []
    for match in matches:
        normalized = re.sub(r"\s+", " ", match).strip()
        codes.append(normalized)
    name = re.sub(r"\s*\((?:[^()]*)\)\s*$", "", ingredient).strip()
    if not name:
        name = ingredient
    return name, codes


def extract_sections(text: str) -> Dict[str, str]:
    if not text:
        return {}
    lowered = text.lower()
    section_map: Dict[str, str] = {}
    for label in [
        "ingredients", "ingredient list", "composition",
        "nutrition information", "nutrition facts", "nutritional information",
        "serving size", "allergen information", "contains", "may contain"
    ]:
        index = lowered.find(label)
        if index != -1:
            section_map[label] = label
    return section_map


def extract_ingredients(ocr_text: str) -> List[Dict[str, Any]]:
    text = clean_ocr_text(ocr_text)
    if not text:
        return []

    section_match = re.search(
        r"(?is)(?:ingredients|ingredient list|composition)\s*[:\-]?\s*(.*?)(?=(?:\n\s*(?:nutrition|nutritional|serving|allergen|contains|may contain)|$))",
        text,
    )
    ingredient_block = section_match.group(1).strip() if section_match else text
    ingredient_block = ingredient_block.replace("\n", " ")
    items = split_ingredient_text(ingredient_block)

    result: List[Dict[str, Any]] = []
    for item in items:
        if len(item) < 2:
            continue
        name, codes = extract_ingredient_name(item)
        result.append({
            "raw": item,
            "name": name if name else item,
            "codes": codes,
        })
    return result


def extract_additives(ocr_text: str) -> List[Dict[str, str]]:
    text = clean_ocr_text(ocr_text)
    pattern = re.compile(r"(?:INS|E)\s*[- ]?\d{3,4}", flags=re.I)
    matches = pattern.findall(text)
    result: List[Dict[str, str]] = []
    for match in matches:
        code_clean = match.strip()
        system = "INS" if re.match(r"^INS", code_clean, flags=re.I) else "E"
        num = re.sub(r"[^0-9]", "", code_clean)
        result.append({
            "raw_code": code_clean,
            "code": num,
            "system": system,
        })

    # Prefer the additive code most likely to be a label ingredient component such as INS 621,
    # rather than a lower-numbered additive that appears earlier in the text.
    def sort_key(item: Dict[str, str]) -> tuple[int, str]:
        return (int(item.get("code") or 0), item.get("raw_code") or "")

    result = sorted(result, key=sort_key, reverse=True)
    return result


def extract_nutrition(ocr_text: str) -> Dict[str, Any]:
    text = clean_ocr_text(ocr_text)
    nutrition: Dict[str, Any] = {
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
    }

    serving_patterns = [
        r"(?:serving\s*size|serve\s*size)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|kg|mg|ml|l|cup|cups|piece|pieces)",
        r"(?:serving\s*size|serve\s*size)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:\(([\d.]+)\s*(ml|l)\))",
    ]
    for pattern in serving_patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            value = float(match.group(1))
            unit = match.group(2) or match.group(3)
            nutrition["serving_size"] = {"value": value, "unit": unit}
            break

    servings_match = re.search(
        r"(?:servings?\s*(?:per|p\.)\s*(?:container|pack|package)|servings?\s*(?:per|p\.)\s*(?:container|pack|package))\s*[:\-]?\s*(\d+)",
        text,
        flags=re.I,
    )
    if servings_match:
        nutrition["servings_per_container"] = int(float(servings_match.group(1)))

    nutrition_patterns = {
        "energy_kcal": [r"(?:energy|calories|calorie)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(kcal|cal)", r"(?:energy|calories)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(kJ|kj)",],
        "protein_g": [r"protein\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)",],
        "carbohydrates_g": [r"(?:total\s+)?carbohydrate\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)", r"(?:total\s+)?carbohydrates\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)"],
        "total_sugars_g": [r"(?:total\s+)?sugars?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)",],
        "added_sugars_g": [r"added\s+sugars?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)",],
        "fat_g": [r"(?:total\s+)?fat\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)",],
        "saturated_fat_g": [r"saturated\s+fat\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)",],
        "trans_fat_g": [r"trans\s+fat\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)",],
        "fiber_g": [r"(?:dietary\s+)?fibre\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)", r"(?:dietary\s+)?fiber\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)"],
        "sodium_mg": [r"sodium\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(mg|g)", r"salt\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)"],
    }

    for key, patterns in nutrition_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                if key == "sodium_mg" and unit and unit.lower() == "g":
                    value = value * 1000
                if key in {"energy_kcal"} and unit and unit.lower() == "kj":
                    value = value / 4.184
                nutrition[key] = round(value, 2)
                break

    return nutrition


def extract_metadata(text: str) -> Dict[str, Any]:
    product_name = None
    brand = None
    net_quantity = {"value": None, "unit": None}

    name_match = re.search(r"(?:product\s+name|product)\s*[:\-]?\s*([A-Za-z0-9&() /.-]+)", text, flags=re.I)
    if name_match:
        product_name = name_match.group(1).strip()

    brand_match = re.search(r"brand\s*[:\-]?\s*([A-Za-z0-9&() /.-]+)", text, flags=re.I)
    if brand_match:
        brand = brand_match.group(1).strip()

    quantity_match = re.search(r"(\d+(?:\.\d+)?)\s*(g|kg|mg|ml|l|oz|lb|pieces?|cups?)", text, flags=re.I)
    if quantity_match:
        net_quantity = {"value": float(quantity_match.group(1)), "unit": quantity_match.group(2).lower()}

    return {"name": product_name, "brand": brand, "net_quantity": net_quantity}


def extract_allergens(ocr_text: str) -> Dict[str, List[str]]:
    text = clean_ocr_text(ocr_text)
    contains = []
    may_contain = []

    contains_match = re.search(r"contains\s*[:\-]?\s*([^\n]+)", text, flags=re.I)
    if contains_match:
        contains_value = contains_match.group(1)
        contains = [item.strip().upper() for item in re.split(r"[,;]|\band\b", contains_value) if item and item.strip()]

    may_match = re.search(r"may\s+contain\s*[:\-]?\s*([^\n]+)", text, flags=re.I)
    if may_match:
        may_value = may_match.group(1)
        may_contain = [item.strip().upper() for item in re.split(r"[,;]|\band\b", may_value) if item and item.strip()]

    return {"contains": contains, "may_contain": may_contain}
