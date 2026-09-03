# OCR Food Intelligence Pipeline

This project combines a document OCR pipeline with a food-label intelligence workflow for structured extraction and normalization.

It was originally built as an offline document converter, and it is now extended with a food intelligence pipeline that processes uploaded food-label images and produces:

- OCR output
- Structured food label extraction
- Normalized ingredient/additive mapping
- Validation and traceability reports

---

## Overview

The application currently supports:

1. Uploading an image into the `upload/` folder
2. Running the OCR pipeline
3. Extracting structured food label information
4. Normalizing ingredients and additive codes
5. Validating the results
6. Saving readable outputs into `output_files/`

This is designed to support a future RAG + LLM food intelligence layer, while keeping the current implementation deterministic and traceable.

---

## Project Structure

```text
ocrDocDemo/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── upload/
│   └── .gitkeep
├── output_files/
│   └── .gitkeep
├── ocr_engine/
│   ├── __init__.py
│   ├── ocr.py
│   └── pdf_converter.py
├── food_intelligence/
│   ├── __init__.py
│   ├── extractors.py
│   ├── mapping_loader.py
│   ├── normalization.py
│   ├── pipeline.py
│   ├── schemas.py
│   ├── service.py
│   ├── mappings/
│   │   ├── ingredients.json
│   │   ├── additives.json
│   │   └── synonyms.json
│   └── tests/
│       └── test_food_pipeline.py
└── .venv/
```

---

## Features

### OCR / document conversion
- Image and PDF processing
- OCR extraction using the existing offline processing flow
- Output written to the project output folder

### Module 1: OCR
- Raw OCR text capture
- Region list with confidence values
- Document metadata extraction

### Module 2: Structured extraction
- Ingredients extraction
- Nutrition parsing
- Serving size extraction
- Additive / INS / E-number extraction
- Allergen detection
- Traceability through raw text and cleaned text

### Module 3: Normalization and validation
- Ingredient synonym mapping
- Additive canonical mapping
- Standardized output structure
- Validation status and review flags

---

## Setup

### 1. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

---

## Run the project

Place one or more food-label images in `upload/` and run:

```powershell
python main.py
```

The script will:

- scan the upload folder
- process the image(s)
- run the OCR + extraction + normalization pipeline
- generate output files in `output_files/`

---

## Output files

For each uploaded image, the app writes files such as:

```text
output_files/
├── image_name_module1_ocr.json
├── image_name_module2_extraction.json
├── image_name_module3_normalized.json
├── image_name_final_output.json
├── image_name_report.txt
└── image_name.docx
```

The JSON files are designed to be readable and structured for later API integration or RAG-based intelligence workflows.

---

## Notes

- Missing data is preserved as `null` rather than guessed.
- Validation is intentionally conservative and flags uncertain or incomplete values as `needs_review`.
- The project is designed to be extended toward future MongoDB, RAG, and LLM-based food-intelligence features.

---

## Example workflow

```text
Upload image
  ↓
OCR scan
  ↓
Structured food extraction
  ↓
Normalization
  ↓
Validation
  ↓
Readable JSON + report output
```

---

## Requirements

The project uses Python and the dependencies listed in `requirements.txt`.

---

## License

This project is intended for educational and internal prototype use unless otherwise specified by the repository owner.
