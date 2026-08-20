import os
import sys
import time
from ocr_engine import (
    is_scanned_pdf, 
    make_searchable_pdf, 
    convert_pdf_to_docx, 
    convert_image_or_scanned_pdf_to_docx,
    is_image_file, 
    convert_image_to_pdf, 
    IMAGE_EXTENSIONS
)

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

def process_documents():
    """
    Main loop that processes all PDFs and Images in the upload folder.
    """
    ensure_directories()
    
    # Get all PDF and Image files in the upload directory
    input_files = [
        f for f in os.listdir(UPLOAD_DIR) 
        if (f.lower().endswith(".pdf") or is_image_file(f)) and not f.startswith("temp_")
    ]
    
    if not input_files:
        print("\n========================================================")
        print("          OFFLINE PDF & IMAGE TO WORD CONVERTER")
        print("========================================================")
        print(f"No PDF or image files found in the '{UPLOAD_DIR}' folder.")
        print(f"Supported formats: .pdf, {', '.join(IMAGE_EXTENSIONS)}")
        print("Please copy your documents or images into the 'upload' folder")
        print("and run this script again:")
        print("  python main.py")
        print("========================================================\n")
        return
        
    print("\n========================================================")
    print(f"       Found {len(input_files)} file(s) to process. Starting batch job...")
    print("========================================================\n")
    
    success_count = 0
    fail_count = 0
    pdf_count = 0
    image_count = 0
    start_time = time.time()
    
    for idx, filename in enumerate(input_files, start=1):
        input_path = os.path.join(UPLOAD_DIR, filename)
        basename = os.path.splitext(filename)[0]
        output_docx_path = os.path.join(OUTPUT_DIR, f"{basename}.docx")
        
        print(f"[{idx}/{len(input_files)}] Processing '{filename}'...")
        file_start_time = time.time()
        
        temp_input_pdf = None
        temp_searchable_pdf = None
        
        if is_image_file(filename):
            image_count += 1
            print(f"[Info] '{filename}' is detected as IMAGE. Performing direct high-accuracy OCR conversion...")
            convert_success = convert_image_or_scanned_pdf_to_docx(input_path, output_docx_path)
        else:
            pdf_count += 1
            scanned = is_scanned_pdf(input_path)
            if scanned:
                print(f"[Info] '{filename}' is detected as SCANNED PDF. Performing direct high-accuracy OCR conversion...")
                convert_success = convert_image_or_scanned_pdf_to_docx(input_path, output_docx_path)
            else:
                print(f"[Info] '{filename}' is detected as DIGITAL PDF. Direct layout conversion enabled...")
                convert_success = convert_pdf_to_docx(input_path, output_docx_path, is_scanned=False)
                
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
    print(f"Total processed files : {len(input_files)}")
    print(f"  - PDFs processed    : {pdf_count}")
    print(f"  - Images processed  : {image_count}")
    print(f"Successfully converted: {success_count}")
    print(f"Failed conversions    : {fail_count}")
    print(f"Total time elapsed    : {total_elapsed:.2f} seconds")
    print(f"Output folder         : {OUTPUT_DIR}")
    print("========================================================\n")

if __name__ == "__main__":
    process_documents()
