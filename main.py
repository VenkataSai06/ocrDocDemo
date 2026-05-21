import os
import sys
import time
from ocr_engine import is_scanned_pdf, make_searchable_pdf, convert_pdf_to_docx

# Define project directories relative to the script location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "upload")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_files")

def ensure_directories():
    """
    Ensures that the upload and output directories exist.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_pdfs():
    """
    Main loop that processes all PDFs in the upload folder.
    """
    ensure_directories()
    
    # Get all PDF files in the upload directory
    pdf_files = [
        f for f in os.listdir(UPLOAD_DIR) 
        if f.lower().endswith(".pdf") and not f.startswith("temp_")
    ]
    
    if not pdf_files:
        print("\n========================================================")
        print("                 PDF TO WORD CONVERTER")
        print("========================================================")
        print(f"No PDF files found in the '{UPLOAD_DIR}' folder.")
        print("Please copy your scanned or normal PDFs into the 'upload' folder")
        print("and run this script again:")
        print("  python main.py")
        print("========================================================\n")
        return
        
    print("\n========================================================")
    print(f"       Found {len(pdf_files)} PDF(s) to process. Starting batch job...")
    print("========================================================\n")
    
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    for idx, filename in enumerate(pdf_files, start=1):
        input_pdf_path = os.path.join(UPLOAD_DIR, filename)
        
        # Output filename has the same name but with a .docx extension
        basename = os.path.splitext(filename)[0]
        output_docx_path = os.path.join(OUTPUT_DIR, f"{basename}.docx")
        
        print(f"[{idx}/{len(pdf_files)}] Processing '{filename}'...")
        file_start_time = time.time()
        
        # Check if the PDF is scanned or digital
        scanned = is_scanned_pdf(input_pdf_path)
        
        temp_searchable_pdf = None
        conversion_source = input_pdf_path
        
        if scanned:
            print(f"[Info] '{filename}' is detected as SCANNED. Preparing OCR...")
            # We create a temporary searchable PDF file
            temp_searchable_pdf = os.path.join(UPLOAD_DIR, f"temp_searchable_{basename}.pdf")
            
            ocr_success = make_searchable_pdf(input_pdf_path, temp_searchable_pdf)
            if ocr_success and os.path.exists(temp_searchable_pdf):
                conversion_source = temp_searchable_pdf
            else:
                print(f"[Error] OCR failed for '{filename}'. Cannot perform text extraction.")
                fail_count += 1
                print("-" * 50)
                continue
        else:
            print(f"[Info] '{filename}' is detected as DIGITAL. Direct conversion enabled.")
            
        # Perform PDF to Word conversion
        convert_success = convert_pdf_to_docx(
            conversion_source, 
            output_docx_path, 
            is_scanned=scanned
        )
        
        # Clean up temporary searchable PDF file if created
        if temp_searchable_pdf and os.path.exists(temp_searchable_pdf):
            try:
                os.remove(temp_searchable_pdf)
                # If an associated PyMuPDF / Tesseract lock file exists, clean it up as well
                tess_lock = temp_searchable_pdf + ".lock"
                if os.path.exists(tess_lock):
                    os.remove(tess_lock)
            except Exception as e:
                # Silently ignore cleanup errors
                pass
                
        elapsed = time.time() - file_start_time
        if convert_success:
            success_count += 1
            print(f"[Success] Converted '{filename}' to Word in {elapsed:.2f} seconds.")
        else:
            fail_count += 1
            print(f"[Error] Failed to convert '{filename}' in {elapsed:.2f} seconds.")
            
        print("-" * 50)
        
    total_elapsed = time.time() - start_time
    print("\n========================================================")
    print("                 CONVERSION SUMMARY")
    print("========================================================")
    print(f"Total processed files : {len(pdf_files)}")
    print(f"Successfully converted: {success_count}")
    print(f"Failed conversions    : {fail_count}")
    print(f"Total time elapsed    : {total_elapsed:.2f} seconds")
    print(f"Output folder         : {OUTPUT_DIR}")
    print("========================================================\n")

if __name__ == "__main__":
    process_pdfs()
