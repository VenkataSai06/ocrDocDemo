from __future__ import annotations

import json
import os
from typing import Any, Dict

import cv2

from ocr_engine import extract_text_lines_from_image
from .service import FoodExtractionService, FoodValidationService
from .normalization import FoodNormalizationService


def build_module_1_ocr_output(image_path: str) -> Dict[str, Any]:
    """Build a structured OCR JSON payload from the uploaded image."""
    filename = os.path.basename(image_path)
    image = cv2.imread(image_path)
    height = 0
    width = 0
    if image is not None:
        height, width = image.shape[:2]

    lines = extract_text_lines_from_image(image_path)
    regions = []
    raw_parts = []
    for line in lines:
        text = (line.get("text") or "").strip()
        if not text:
            continue
        raw_parts.append(text)
        regions.append({
            "text": text,
            "confidence": float(line.get("score", 0.0) or 0.0),
        })

    return {
        "document_id": os.path.splitext(filename)[0],
        "image": {
            "filename": filename,
            "width": width,
            "height": height,
        },
        "ocr": {
            "engine": "EasyOCR / RapidOCR",
            "language": "en",
        },
        "regions": regions,
        "raw_text": "\n".join(raw_parts),
    }


def run_food_pipeline(image_path: str) -> Dict[str, Any]:
    """Run OCR -> extraction -> normalization -> validation pipeline and return combined results."""
    ocr_output = build_module_1_ocr_output(image_path)
    extraction_service = FoodExtractionService()
    normalization_service = FoodNormalizationService()
    validation_service = FoodValidationService()

    structured = extraction_service.process(ocr_output)
    normalized = normalization_service.process(structured)
    validated = validation_service.process(normalized)

    return {
        "document_id": ocr_output.get("document_id"),
        "module_1_ocr": ocr_output,
        "module_2_extraction": structured,
        "module_3_normalization": normalized,
        "module_3_validation": validated,
        "final_output": {
            "product": validated.get("product"),
            "ingredients": validated.get("ingredients"),
            "nutrition": validated.get("nutrition"),
            "additives": validated.get("additives"),
            "allergens": validated.get("allergens"),
            "validation": validated.get("validation"),
            "traceability": validated.get("traceability"),
        },
    }


def write_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_readable_report(path: str, data: Dict[str, Any]) -> None:
    lines = [
        "Food Intelligence Pipeline Report",
        "=" * 40,
        f"Document ID: {data.get('document_id', 'unknown')}",
        "",
        "Module 1: OCR",
        "-" * 40,
    ]
    ocr = data.get("module_1_ocr", {})
    if ocr.get("raw_text"):
        lines.append(ocr["raw_text"][:2000])
    else:
        lines.append("No OCR text captured.")

    lines.extend(["", "Module 2: Structured Extraction", "-" * 40])
    extraction = data.get("module_2_extraction", {})
    lines.append(f"Ingredients: {len(extraction.get('ingredients', []))}")
    lines.append(f"Nutrition keys: {list(extraction.get('nutrition', {}).keys())}")
    lines.append(f"Additives found: {len(extraction.get('additives', []))}")

    lines.extend(["", "Module 3: Validation", "-" * 40])
    validation = data.get("module_3_validation", {}).get("validation", {})
    lines.append(f"Status: {validation.get('status', 'unknown')}")
    issues = validation.get("issues") or []
    if issues:
        lines.extend([f"- {issue}" for issue in issues])
    else:
        lines.append("No validation issues detected.")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
