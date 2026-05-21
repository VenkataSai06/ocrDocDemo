import os
from pdf2docx import Converter

def convert_pdf_to_docx(pdf_path, docx_path, is_scanned=False):
    """
    Converts a PDF file to a Word (.docx) file.
    
    Parameters:
    - pdf_path: Path to the input PDF file (scanned or digital).
    - docx_path: Path where the output Word document should be saved.
    - is_scanned: Set to True if this is a searchable PDF that was generated from a scan.
    """
    print(f"[Converter] Converting '{os.path.basename(pdf_path)}' to Word format...")
    
    try:
        cv = Converter(pdf_path)
        
        # Configure OCR settings
        # ocr=2 tells pdf2docx that the document contains a hidden/scanned text layer and should reconstruct from it.
        # ocr=0 tells it to extract normal selectable text directly.
        ocr_mode = 2 if is_scanned else 0
        
        # Parse and convert all pages (start=0, end=None)
        cv.convert(
            docx_path,
            start=0,
            end=None,
            ocr=ocr_mode,
            parse_lattice_table=True,      # Detect tables with border lines
            parse_stream_table=True,       # Detect borderless tables based on alignment
            connected_border_tolerance=2.0  # Help connect table lines that might have gaps
        )
        
        cv.close()
        print(f"[Converter] Conversion complete. Word file saved to '{os.path.basename(docx_path)}'.")
        return True
    except Exception as e:
        print(f"[Error] Failed to convert PDF to Word: {e}")
        return False
