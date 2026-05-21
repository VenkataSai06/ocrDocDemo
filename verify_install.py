import os
import sys
import shutil
import fitz  # PyMuPDF

# Ensure we are importing from the project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from ocr_engine import is_scanned_pdf, make_searchable_pdf, convert_pdf_to_docx
from ocr_engine.ocr import get_tesseract_path

UPLOAD_DIR = os.path.join(BASE_DIR, "upload")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_files")

def ensure_directories():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_mock_pdfs():
    """
    Generates:
    1. A digital PDF with readable text, a drawn table, and a hyperlink.
    2. A scanned PDF created by rendering the digital PDF as an image.
    """
    ensure_directories()
    
    digital_path = os.path.join(UPLOAD_DIR, "test_digital.pdf")
    scanned_path = os.path.join(UPLOAD_DIR, "test_scanned.pdf")
    
    print("[Test Prep] Creating digital test PDF...")
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4 dimensions in points
    
    # 1. Heading
    page.insert_text(fitz.Point(50, 80), "Offline PDF to Word Test Document", fontsize=18, fontname="helv")
    
    # 2. Paragraph
    paragraph_text = (
        "This is a sample document generated programmatically to verify "
        "that our offline PDF to Word converter accurately parses paragraphs, "
        "headings, table structures, and links."
    )
    page.insert_text(fitz.Point(50, 110), paragraph_text, fontsize=10, fontname="helv")
    
    # 3. URL Link
    page.insert_text(fitz.Point(50, 140), "For project documentation, visit: www.example.com", fontsize=10, fontname="helv")
    # Insert invisible clickable link in digital PDF
    link_rect = fitz.Rect(185, 130, 310, 150)
    page.insert_link({
        "kind": fitz.LINK_URI,
        "from": link_rect,
        "uri": "http://www.example.com"
    })
    
    # 4. Table (Drawn using line vectors)
    # Cell 1: (50, 200) to (175, 250) -> Text: Header 1
    # Cell 2: (175, 200) to (300, 250) -> Text: Header 2
    # Cell 3: (50, 250) to (175, 300) -> Text: Data 1
    # Cell 4: (175, 250) to (300, 300) -> Text: Data 2
    
    # Draw table border lines
    page.draw_rect(fitz.Rect(50, 180, 350, 280), color=(0, 0, 0), width=1)
    page.draw_line(fitz.Point(50, 230), fitz.Point(350, 230), color=(0, 0, 0), width=1) # Horizontal divider
    page.draw_line(fitz.Point(200, 180), fitz.Point(200, 280), color=(0, 0, 0), width=1) # Vertical divider
    
    # Insert Table Headers
    page.insert_text(fitz.Point(60, 210), "Employee ID", fontsize=11, fontname="helv")
    page.insert_text(fitz.Point(210, 210), "Status", fontsize=11, fontname="helv")
    
    # Insert Table Data
    page.insert_text(fitz.Point(60, 260), "EMP-88402", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(210, 260), "Active Offline", fontsize=10, fontname="helv")
    
    doc.save(digital_path)
    doc.close()
    print(f"[Test Prep] Digital PDF created at: {digital_path}")
    
    # Now create the scanned PDF by rendering pages as images
    print("[Test Prep] Creating scanned test PDF...")
    doc = fitz.open(digital_path)
    scanned_doc = fitz.open()
    
    for page in doc:
        # Render page to image at 150 DPI (reduces memory usage and speeds up OCR for test)
        pix = page.get_pixmap(dpi=150)
        
        new_page = scanned_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, pixmap=pix)
        
    scanned_doc.save(scanned_path)
    scanned_doc.close()
    doc.close()
    print(f"[Test Prep] Scanned PDF created at: {scanned_path}")
    return digital_path, scanned_path

def run_tests():
    ensure_directories()
    
    # Check Tesseract availability
    tess_path = get_tesseract_path()
    if tess_path:
        print(f"[System Status] Tesseract OCR is AVAILABLE at: {tess_path}")
    else:
        print("[System Status] Tesseract OCR is NOT found in default paths. Fallback to EasyOCR will be used.")
        
    # Generate test files
    digital_pdf, scanned_pdf = create_mock_pdfs()
    
    print("\n" + "="*50)
    print("RUNNING PIPELINE TESTS")
    print("="*50)
    
    # 1. Test is_scanned_pdf
    is_digital_scanned = is_scanned_pdf(digital_pdf)
    is_scanned_scanned = is_scanned_pdf(scanned_pdf)
    
    print(f"[Test 1] Digital PDF Scanned check: {is_digital_scanned} (Expected: False)")
    print(f"[Test 1] Scanned PDF Scanned check: {is_scanned_scanned} (Expected: True)")
    
    assert not is_digital_scanned, "Digital PDF classified as scanned!"
    assert is_scanned_scanned, "Scanned PDF classified as digital!"
    print("[Test 1 PASS] Scanned vs Digital classification is correct.")
    print("-" * 50)
    
    # 2. Test Digital PDF Conversion
    digital_docx = os.path.join(OUTPUT_DIR, "test_digital.docx")
    if os.path.exists(digital_docx):
        os.remove(digital_docx)
        
    print("[Test 2] Running Digital to Word conversion...")
    success = convert_pdf_to_docx(digital_pdf, digital_docx, is_scanned=False)
    
    assert success, "Digital PDF conversion failed!"
    assert os.path.exists(digital_docx), "Digital output DOCX file does not exist!"
    print(f"[Test 2 PASS] Digital PDF successfully converted to Word: {digital_docx}")
    print("-" * 50)
    
    # 3. Test Scanned PDF Conversion (OCR)
    scanned_docx = os.path.join(OUTPUT_DIR, "test_scanned.docx")
    if os.path.exists(scanned_docx):
        os.remove(scanned_docx)
        
    # First, make it searchable
    temp_searchable = os.path.join(UPLOAD_DIR, "temp_test_scanned_searchable.pdf")
    if os.path.exists(temp_searchable):
        os.remove(temp_searchable)
        
    print("[Test 3] Step A: Running OCR on Scanned PDF...")
    ocr_success = make_searchable_pdf(scanned_pdf, temp_searchable)
    assert ocr_success, "OCR page-layer generation failed!"
    assert os.path.exists(temp_searchable), "Searchable PDF file not created!"
    
    # Check that searchable PDF has text
    searchable_text_check = is_scanned_pdf(temp_searchable)
    print(f"[Test 3] Searchable PDF Scanned check: {searchable_text_check} (Expected: False)")
    assert not searchable_text_check, "OCR searchable PDF still classified as scanned!"
    
    print("[Test 3] Step B: Running Searchable PDF to Word conversion...")
    success = convert_pdf_to_docx(temp_searchable, scanned_docx, is_scanned=True)
    
    # Clean up temp file
    if os.path.exists(temp_searchable):
        os.remove(temp_searchable)
        tess_lock = temp_searchable + ".lock"
        if os.path.exists(tess_lock):
            os.remove(tess_lock)
            
    assert success, "Scanned PDF conversion failed!"
    assert os.path.exists(scanned_docx), "Scanned output DOCX file does not exist!"
    
    # Verify table detection in the converted scanned document
    import docx
    res_doc = docx.Document(scanned_docx)
    print(f"[Test 3] Number of tables detected in scanned Word output: {len(res_doc.tables)} (Expected: >= 1)")
    assert len(res_doc.tables) >= 1, "Failed to reconstruct tables from scanned PDF!"
    
    print(f"[Test 3 PASS] Scanned PDF successfully OCR'ed and converted to Word with tables: {scanned_docx}")
    print("=" * 50)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n[Test FAILURE] A test failed during verification: {e}")
        sys.exit(1)
