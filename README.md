# Offline PDF & Image to Word Converter (with Layout, OCR & Table Preservation)

This is a robust, offline Python application that batch-converts **digital (searchable) PDFs**, **scanned PDFs**, and **images** (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.webp`) into editable Microsoft Word (`.docx`) documents. 

It is specifically optimized to maintain layout structure, columns, tables, headings, paragraphs, and active hyperlinks without requiring any internet connection.

---

## ✨ Features

- **🖼️ Image & Scanned Document Support**: Automatically processes standalone images (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.webp`) and scanned PDFs into editable Word documents.
- **🧠 Auto-Classification**: Automatically detects whether a PDF is digital or scanned based on character density.
- **🔍 Dual Offline OCR Engine**:
  - Automatically searches for a local **Tesseract OCR** installation for fast processing.
  - Automatically falls back to a high-accuracy **EasyOCR** (PyTorch-based) engine when Tesseract is not installed.
- **📐 Advanced Layout Preservation**:
  - **Horizontal Overlap Prevention**: Separates adjacent lines (like footers) to prevent them from merging vertically or getting ignored due to overlap.
  - **Height-Width Balanced Font Scaling**: Calculates text boundaries and adjusts font sizes so text fits perfectly without getting clipped/cut off at page margins, while maintaining a minimum size floor of `6.0pt` to avoid size instability.
  - **Hyperlink Extraction**: Detects web URLs (using regex patterns) and overlays active, clickable hyperlinks in the output Word document.
- **📊 Scanned Table & Image Table Reconstruction**:
  - Leverages the **`img2table`** library to analyze scanned images and detect table cell borders.
  - Dynamically overlays cell vector lines onto the temporary searchable PDF layer, allowing `pdf2docx` to reconstruct them as native, editable Word tables instead of plain text.

---

## 🛠️ Setup & Installation

### 1. Prerequisites
- **Python 3.8 to 3.11** installed on your system.
- *(Optional but recommended)* **Tesseract OCR** installed on Windows. The engine will locate it automatically in program directories. If not present, it will fallback to EasyOCR.

### 2. Clone and Setup Environment
Open a terminal (PowerShell on Windows) and run:

```powershell
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 How to Run the Converter

1. **Place Files in `upload/`**:
   Put scanned PDFs, digital PDFs, or image files (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.webp`) into the `upload/` folder.
   
2. **Execute the Runner**:
   ```bash
   python main.py
   ```
   
3. **Get Word Documents in `output_files/`**:
   The converted, editable Word documents (`.docx`) will be saved in the `output_files/` folder under the same filenames.
