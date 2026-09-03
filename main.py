import os
import time

from ocr_engine import (
    IMAGE_EXTENSIONS,
    convert_image_or_scanned_pdf_to_docx,
    convert_pdf_to_docx,
    is_image_file,
    is_scanned_pdf,
)
from food_intelligence.pipeline import (
    run_food_pipeline,
    write_json,
    write_readable_report,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "upload")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_files")


def ensure_directories():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def process_uploaded_image(image_path: str):
    basename = os.path.splitext(os.path.basename(image_path))[0]
    result = run_food_pipeline(image_path)

    module1_path = os.path.join(OUTPUT_DIR, f"{basename}_module1_ocr.json")
    module2_path = os.path.join(OUTPUT_DIR, f"{basename}_module2_extraction.json")
    module3_path = os.path.join(OUTPUT_DIR, f"{basename}_module3_normalized.json")
    final_path = os.path.join(OUTPUT_DIR, f"{basename}_final_output.json")
    report_path = os.path.join(OUTPUT_DIR, f"{basename}_report.txt")

    write_json(module1_path, result["module_1_ocr"])
    write_json(module2_path, result["module_2_extraction"])
    write_json(module3_path, result["module_3_validation"])
    write_json(final_path, result["final_output"])
    write_readable_report(report_path, result)

    print(f"[Pipeline] OCR JSON written: {module1_path}")
    print(f"[Pipeline] Structured extraction JSON written: {module2_path}")
    print(f"[Pipeline] Normalized/validated output written: {module3_path}")
    print(f"[Pipeline] Final readable report written: {report_path}")
    return True


def process_documents():
    ensure_directories()

    input_files = [
        f for f in os.listdir(UPLOAD_DIR)
        if (f.lower().endswith(".pdf") or is_image_file(f)) and not f.startswith("temp_")
    ]

    if not input_files:
        print("\n========================================================")
        print("    Food Intelligence OCR + Extraction + Normalization")
        print("========================================================")
        print(f"No files found in '{UPLOAD_DIR}'.")
        print(f"Supported formats: .pdf, {', '.join(IMAGE_EXTENSIONS)}")
        print("Place an image or PDF in the upload folder and run: python main.py")
        print("========================================================\n")
        return

    print("\n========================================================")
    print(f"Found {len(input_files)} file(s) in the upload folder.")
    print("========================================================\n")

    success_count = 0
    fail_count = 0
    start_time = time.time()

    for idx, filename in enumerate(input_files, start=1):
        input_path = os.path.join(UPLOAD_DIR, filename)
        basename = os.path.splitext(filename)[0]
        output_docx_path = os.path.join(OUTPUT_DIR, f"{basename}.docx")

        print(f"[{idx}/{len(input_files)}] Processing '{filename}'...")

        if is_image_file(filename):
            try:
                processed = process_uploaded_image(input_path)
                success_count += 1 if processed else 0
                print(f"[Success] Food pipeline completed for '{filename}'.")
            except Exception as exc:
                fail_count += 1
                print(f"[Error] Image pipeline failed for '{filename}': {exc}")
        else:
            try:
                scanned = is_scanned_pdf(input_path)
                if scanned:
                    convert_success = convert_image_or_scanned_pdf_to_docx(input_path, output_docx_path)
                else:
                    convert_success = convert_pdf_to_docx(input_path, output_docx_path, is_scanned=False)
                if convert_success:
                    success_count += 1
                    print(f"[Success] Converted PDF to DOCX: {output_docx_path}")
                else:
                    fail_count += 1
            except Exception as exc:
                fail_count += 1
                print(f"[Error] PDF conversion failed for '{filename}': {exc}")

        print("-" * 50)

    total_elapsed = time.time() - start_time
    print("\n========================================================")
    print("                 PIPELINE SUMMARY")
    print("========================================================")
    print(f"Processed files      : {len(input_files)}")
    print(f"Successful runs      : {success_count}")
    print(f"Failed runs          : {fail_count}")
    print(f"Total time elapsed   : {total_elapsed:.2f} seconds")
    print(f"Output folder        : {OUTPUT_DIR}")
    print("========================================================\n")


if __name__ == "__main__":
    process_documents()
