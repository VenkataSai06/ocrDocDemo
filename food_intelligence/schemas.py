from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProductMetadata(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    net_quantity: Dict[str, Optional[Any]] = Field(default_factory=lambda: {"value": None, "unit": None})


class IngredientItem(BaseModel):
    raw: str
    name: Optional[str] = None
    codes: List[str] = Field(default_factory=list)
    canonical: Optional[str] = None
    status: Optional[str] = None


class AdditiveItem(BaseModel):
    raw_code: Optional[str] = None
    code: Optional[str] = None
    system: Optional[str] = None
    canonical_name: Optional[str] = None
    status: Optional[str] = None


class Allergens(BaseModel):
    contains: List[str] = Field(default_factory=list)
    may_contain: List[str] = Field(default_factory=list)


class NutritionServing(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None


class ExtractionNutrition(BaseModel):
    serving_size: Dict[str, Optional[Any]] = Field(default_factory=lambda: {"value": None, "unit": None})
    servings_per_container: Optional[int] = None
    energy_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbohydrates_g: Optional[float] = None
    total_sugars_g: Optional[float] = None
    added_sugars_g: Optional[float] = None
    fat_g: Optional[float] = None
    saturated_fat_g: Optional[float] = None
    trans_fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sodium_mg: Optional[float] = None


class ExtractionSource(BaseModel):
    raw_ocr_text: Optional[str] = None
    cleaned_ocr_text: Optional[str] = None


class FoodProductExtraction(BaseModel):
    document_id: Optional[str] = None
    product: ProductMetadata = Field(default_factory=ProductMetadata)
    ingredients: List[IngredientItem] = Field(default_factory=list)
    nutrition: ExtractionNutrition = Field(default_factory=ExtractionNutrition)
    additives: List[AdditiveItem] = Field(default_factory=list)
    allergens: Allergens = Field(default_factory=Allergens)
    source: ExtractionSource = Field(default_factory=ExtractionSource)


class NormalizedIngredient(BaseModel):
    raw: str
    canonical: Optional[str] = None
    code: Optional[str] = None
    status: str = "unknown"


class NormalizedAdditive(BaseModel):
    raw_code: Optional[str] = None
    code: Optional[str] = None
    system: Optional[str] = None
    canonical_name: Optional[str] = None
    status: str = "unknown"


class FoodProductNormalization(BaseModel):
    document_id: Optional[str] = None
    product: ProductMetadata = Field(default_factory=ProductMetadata)
    ingredients: List[NormalizedIngredient] = Field(default_factory=list)
    nutrition: ExtractionNutrition = Field(default_factory=ExtractionNutrition)
    additives: List[NormalizedAdditive] = Field(default_factory=list)
    allergens: Allergens = Field(default_factory=Allergens)
    validation: Dict[str, Any] = Field(default_factory=lambda: {"status": "valid", "issues": []})
    traceability: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    status: str = "valid"
    issues: List[str] = Field(default_factory=list)
