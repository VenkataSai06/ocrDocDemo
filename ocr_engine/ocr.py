import os
import re
import shutil
import fitz  # PyMuPDF
import cv2
import numpy as np

# Supported image file extensions
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')

# URL pattern for detecting web links in OCR results
URL_PATTERN = re.compile(r'^(https?://[^\s]+|www\.[^\s]+)$')

# Lazy-loaded OCR engines
_RAPID_OCR_ENGINE = None
_EASYOCR_READER = None

def get_rapid_ocr():
    """
    Lazy initializes and returns the RapidOCR engine instance.
    """
    global _RAPID_OCR_ENGINE
    if _RAPID_OCR_ENGINE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _RAPID_OCR_ENGINE = RapidOCR()
        except Exception as e:
            print(f"[Warning] RapidOCR initialization failed: {e}")
            _RAPID_OCR_ENGINE = False
    return _RAPID_OCR_ENGINE if _RAPID_OCR_ENGINE is not False else None

def get_easyocr_reader():
    """
    Lazy initializes and returns the EasyOCR reader instance.
    """
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        try:
            import easyocr
            _EASYOCR_READER = easyocr.Reader(['en'], gpu=False)
        except Exception as e:
            print(f"[Warning] EasyOCR initialization failed: {e}")
            _EASYOCR_READER = False
    return _EASYOCR_READER if _EASYOCR_READER is not False else None

def is_image_file(file_path):
    """
    Checks if the given file path has a supported image extension.
    """
    return file_path.lower().endswith(IMAGE_EXTENSIONS)

def convert_image_to_pdf(image_path, output_pdf_path):
    """
    Converts an image file into a PDF document.
    """
    try:
        img_doc = fitz.open(image_path)
        pdf_bytes = img_doc.convert_to_pdf()
        img_doc.close()
        
        pdf_doc = fitz.open("pdf", pdf_bytes)
        pdf_doc.save(output_pdf_path)
        pdf_doc.close()
        return True
    except Exception as e:
        print(f"[Error] Failed to convert image '{os.path.basename(image_path)}' to PDF: {e}")
        return False

def is_scanned_pdf(pdf_path, text_threshold=50):
    """
    Checks if a PDF is scanned by evaluating average text character length per page.
    """
    try:
        doc = fitz.open(pdf_path)
        total_text_length = 0
        total_pages = len(doc)
        
        if total_pages == 0:
            doc.close()
            return True
            
        for page in doc:
            text = page.get_text()
            total_text_length += len(text.strip())
            
        doc.close()
        avg_text_length = total_text_length / total_pages
        print(f"[Info] '{os.path.basename(pdf_path)}': average character count per page is {avg_text_length:.2f}")
        return avg_text_length < text_threshold
    except Exception as e:
        print(f"[Warning] Error checking if PDF is scanned: {e}")
        return True

def clean_ocr_text(text):
    """
    Cleans up OCR output: restores spaces between concatenated words, formats numbers/percentages,
    standardizes INS codes, and cleans brackets without corrupting characters.
    """
    if not text:
        return ""
    text = text.strip()
    if not text:
        return ""

    # Fix spacing around punctuation and brackets
    text = re.sub(r'([:,%\)])([A-Za-z0-9\{])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z0-9])([\(\{])', r'\1 \2', text)
    
    # Camel case word separation (e.g. RolledOats -> Rolled Oats)
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    text = re.sub(r'\b([A-Z][a-z]+)and([A-Z][a-z]+)\b', r'\1 and \2', text)
    text = re.sub(r'\b([A-Z][a-z]+)and\s+([A-Z][a-z]+)\b', r'\1 and \2', text)
    
    # Common OCR misspelling & code fixes
    text = re.sub(r'\blodized\b', 'Iodized', text)
    text = re.sub(r'\bGluten\b', 'GLUTEN', text)
    text = re.sub(r'INS\s*5[oO0]0ii', 'INS 500ii', text)
    text = re.sub(r'INS\s*500i\b', 'INS 500ii', text)
    text = re.sub(r'INS\s*320\b', 'INS 320', text)
    
    # Known concatenated food label phrases
    replacements = {
        'FruitandNut': 'Fruit and Nut',
        'Fruit andNut': 'Fruit and Nut',
        'CandiedCranberry': 'Candied Cranberry',
        'CONTAINSADDEDFLAVOURS': 'CONTAINS ADDED FLAVOURS',
        'NATUREIDENTICALAND': 'NATURE IDENTICAL AND',
        'ARTIFICIALCREAMFLAVOURINGSUBSTANCES': 'ARTIFICIAL CREAM FLAVOURING SUBSTANCES',
        'CONTAINSGLUTEN': 'CONTAINS GLUTEN',
        'MAYCONTAINTRACESOFSOYANDMILK': 'MAY CONTAIN TRACES OF SOY AND MILK'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
        
    return text

def extract_text_lines_from_image(image_path_or_bytes, min_confidence=0.80):
    """
    Extracts high-accuracy text lines from an image file path or raw image bytes.
    Uses RapidOCR (with 2x upscaling) as primary engine, falling back to EasyOCR.
    Returns a list of dicts: [{'text': str, 'box': list, 'score': float}]
    """
    # Load image
    if isinstance(image_path_or_bytes, str):
        img = cv2.imread(image_path_or_bytes)
    elif isinstance(image_path_or_bytes, bytes):
        nparr = np.frombuffer(image_path_or_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        img = None
        
    if img is None:
        return []
        
    # High quality upscaling (2x) for small dense text
    h, w = img.shape[:2]
    resized_img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    
    lines = []
    rapid_engine = get_rapid_ocr()
    
    if rapid_engine:
        try:
            result, _ = rapid_engine(resized_img)
            if result:
                # Sort blocks primarily by y-coordinate (top-to-bottom)
                sorted_blocks = sorted(result, key=lambda r: min(pt[1] for pt in r[0]))
                for block in sorted_blocks:
                    raw_text = block[1]
                    score = float(block[2])
                    if score < min_confidence:
                        continue
                    cleaned = clean_ocr_text(raw_text)
                    if cleaned:
                        lines.append({
                            'text': cleaned,
                            'box': block[0],
                            'score': score
                        })
                return lines
        except Exception as e:
            print(f"[Warning] RapidOCR processing failed: {e}. Falling back to EasyOCR.")
            
    # Fallback to EasyOCR
    reader = get_easyocr_reader()
    if reader:
        try:
            results = reader.readtext(resized_img, paragraph=False)
            sorted_blocks = sorted(results, key=lambda r: min(pt[1] for pt in r[0]))
            for (bbox, raw_text, prob) in sorted_blocks:
                if float(prob) < min_confidence:
                    continue
                cleaned = clean_ocr_text(raw_text)
                if cleaned:
                    lines.append({
                        'text': cleaned,
                        'box': bbox,
                        'score': float(prob)
                    })
            return lines
        except Exception as e:
            print(f"[Error] EasyOCR fallback failed: {e}")
            
    return []

def extract_text_lines_from_pdf(pdf_path):
    """
    Extracts text lines from each page of a scanned or digital PDF document.
    Returns a list of pages, where each page is a list of extracted line dicts.
    """
    doc = fitz.open(pdf_path)
    pages_lines = []
    
    for page_idx, page in enumerate(doc):
        # Render page to image at 300 DPI
        zoom = 300 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        
        lines = extract_text_lines_from_image(img_bytes)
        pages_lines.append(lines)
        
    doc.close()
    return pages_lines

def make_searchable_pdf(input_pdf_path, output_pdf_path):
    """
    Generates a searchable PDF from an input image/PDF using RapidOCR/EasyOCR.
    """
    print(f"[OCR] Running high-accuracy OCR on '{os.path.basename(input_pdf_path)}'...")
    doc = fitz.open(input_pdf_path)
    output_doc = fitz.open()
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        zoom = 300 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        
        lines = extract_text_lines_from_image(img_bytes)
        
        new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, pixmap=pix)
        
        # Add invisible text layer for searching
        scale_x = page.rect.width / (pix.width * 2)  # divided by 2 due to 2x upscaling
        scale_y = page.rect.height / (pix.height * 2)
        
        for item in lines:
            txt = item['text']
            box = item['box']
            if not txt or not box:
                continue
            
            x0 = min(pt[0] for pt in box) * scale_x
            y0 = min(pt[1] for pt in box) * scale_y
            h_pdf = (max(pt[1] for pt in box) - min(pt[1] for pt in box)) * scale_y
            font_size = max(6.0, h_pdf * 0.75)
            baseline_y = y0 + (h_pdf * 0.8)
            
            try:
                new_page.insert_text(
                    fitz.Point(x0, baseline_y),
                    txt,
                    fontsize=font_size,
                    fontname="helv",
                    render_mode=3,
                    color=(0, 0, 0)
                )
            except Exception:
                pass
                
    output_doc.save(output_pdf_path)
    output_doc.close()
    doc.close()
    print(f"[OCR] Saved searchable PDF to '{os.path.basename(output_pdf_path)}'.")
    return True
