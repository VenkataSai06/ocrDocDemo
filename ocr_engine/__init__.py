from .ocr import (
    is_scanned_pdf, 
    make_searchable_pdf, 
    is_image_file, 
    convert_image_to_pdf, 
    extract_text_lines_from_image,
    extract_text_lines_from_pdf,
    IMAGE_EXTENSIONS
)
from .pdf_converter import convert_pdf_to_docx, convert_image_or_scanned_pdf_to_docx

__all__ = [
    'is_scanned_pdf',
    'make_searchable_pdf',
    'convert_pdf_to_docx',
    'convert_image_or_scanned_pdf_to_docx',
    'is_image_file',
    'convert_image_to_pdf',
    'extract_text_lines_from_image',
    'extract_text_lines_from_pdf',
    'IMAGE_EXTENSIONS'
]

