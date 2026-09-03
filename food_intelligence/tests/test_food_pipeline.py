import pytest

from food_intelligence import FoodExtractionService, FoodNormalizationService, FoodValidationService


SAMPLE_OCR = {
    "document_id": "food_001",
    "ocr": {"engine": "EasyOCR", "language": "en"},
    "raw_text": "INGREDIENTS: Wheat Flour, Palm Oil, Sugar, Salt, Milk Solids, Emulsifier (INS 322), Flavour Enhancer (INS 621)\nNUTRITION INFORMATION\nServing Size: 30 g\nEnergy 450 kcal\nProtein 8 g\nCarbohydrate 65 g\nTotal Sugars 12 g\nFat 18 g\nSodium 500 mg\nCONTAINS: WHEAT, MILK",
    "regions": [
        {"text": "INGREDIENTS", "confidence": 0.98},
        {"text": "Wheat Flour", "confidence": 0.96},
        {"text": "Palm Oil", "confidence": 0.94},
        {"text": "INS 621", "confidence": 0.95},
    ],
}


def test_extraction_from_ocr():
    service = FoodExtractionService()
    result = service.process(SAMPLE_OCR)

    assert result["product"]["name"] is None
    assert result["ingredients"][0]["raw"] == "Wheat Flour"
    assert result["nutrition"]["energy_kcal"] == 450
    assert result["nutrition"]["serving_size"]["value"] == 30
    assert result["additives"][0]["raw_code"] == "INS 621"
    assert result["allergens"]["contains"] == ["WHEAT", "MILK"]


def test_normalization_and_validation_pipeline():
    extracted = FoodExtractionService().process(SAMPLE_OCR)
    normalized = FoodNormalizationService().process(extracted)
    validated = FoodValidationService().process(normalized)

    assert normalized["ingredients"][0]["canonical"] == "Wheat Flour"
    assert normalized["ingredients"][1]["canonical"] == "Palm Oil"
    assert normalized["additives"][0]["canonical_name"] == "Monosodium Glutamate"
    assert validated["validation"]["status"] in {"valid", "needs_review"}


def test_negative_nutrition_raises_issue():
    raw = {
        "document_id": "bad_001",
        "raw_text": "Protein -5 g\nEnergy 100 kcal",
        "ocr": {"engine": "EasyOCR", "language": "en"},
        "regions": [],
    }
    result = FoodExtractionService().process(raw)
    normalized = FoodNormalizationService().process(result)
    validated = FoodValidationService().process(normalized)

    assert any("negative" in issue.lower() for issue in validated["validation"]["issues"])
