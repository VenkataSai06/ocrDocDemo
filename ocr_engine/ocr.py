import os
import re
import shutil
import fitz  # PyMuPDF
import easyocr
from img2table.document import Image as TableImage

# URL pattern for detecting web links in OCR results
URL_PATTERN = re.compile(r'^(https?://[^\s]+|www\.[^\s]+)$')

def is_scanned_pdf(pdf_path, text_threshold=50):
    """
    Checks if a PDF is scanned by looking at the average text length per page.
    If the average text length is below the threshold, it is classified as scanned.
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

def get_tesseract_path():
    """
    Searches for the Tesseract installation on Windows.
    Returns the path to the Tesseract-OCR directory if found, otherwise None.
    """
    # 1. Check PATH
    tess_exe = shutil.which("tesseract")
    if tess_exe:
        tess_dir = os.path.dirname(tess_exe)
        if os.path.exists(os.path.join(tess_dir, "tessdata")):
            return tess_dir

    # 2. Check standard Windows paths
    standard_paths = [
        r"C:\Program Files\Tesseract-OCR",
        r"C:\Program Files (x86)\Tesseract-OCR",
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR")
    ]
    
    for path in standard_paths:
        if os.path.exists(os.path.join(path, "tesseract.exe")) and os.path.exists(os.path.join(path, "tessdata")):
            return path
            
    return None

def sort_text_blocks(blocks):
    """
    Sorts text blocks into a natural reading order (line-by-line: top-to-bottom, left-to-right).
    Each block is expected to be a dict containing coordinates:
    {'x_pdf': x, 'y_pdf': y, 'w_pdf': w, 'h_pdf': h, ...}
    """
    if not blocks:
        return []
        
    # Sort primarily by vertical coordinate (y_pdf)
    sorted_blocks = sorted(blocks, key=lambda b: b['y_pdf'])
    
    lines = []
    for block in sorted_blocks:
        placed = False
        for line in lines:
            rep = line[0]
            # Calculate vertical overlap
            overlap_y = min(block['y_pdf'] + block['h_pdf'], rep['y_pdf'] + rep['h_pdf']) - max(block['y_pdf'], rep['y_pdf'])
            min_h = min(block['h_pdf'], rep['h_pdf'])
            # If vertical overlap is significant (>40% of the block height), they are on the same line
            if overlap_y > 0.4 * min_h or abs(block['y_pdf'] - rep['y_pdf']) < 0.4 * min_h:
                # Check if the block horizontally overlaps with any block already in this line.
                # If it overlaps horizontally by more than a small threshold (e.g. 5 points), they belong to different lines.
                horiz_overlap = False
                for b_in_line in line:
                    overlap_x = min(block['x_pdf'] + block['w_pdf'], b_in_line['x_pdf'] + b_in_line['w_pdf']) - max(block['x_pdf'], b_in_line['x_pdf'])
                    if overlap_x > 5.0:
                        horiz_overlap = True
                        break
                if not horiz_overlap:
                    line.append(block)
                    placed = True
                    break
        if not placed:
            lines.append([block])
            
    # Sort blocks within each line from left to right, and merge close neighbors horizontally

    sorted_flat = []
    for line in lines:
        line.sort(key=lambda b: b['x_pdf'])
        
        # Merge horizontally close blocks
        merged_line = []
        for block in line:
            if not merged_line:
                merged_line.append(block)
            else:
                prev = merged_line[-1]
                # Calculate horizontal gap between prev block end and current block start
                prev_end_x = prev['x_pdf'] + prev['w_pdf']
                gap = block['x_pdf'] - prev_end_x
                
                max_h = max(prev['h_pdf'], block['h_pdf'])
                # If they are very close horizontally, merge them (threshold: 15 points or 1.5 * height)
                if gap < max(15.0, 1.5 * max_h):
                    new_text = prev['text'] + " " + block['text']
                    new_x = prev['x_pdf']
                    new_y = min(prev['y_pdf'], block['y_pdf'])
                    # Determine new width and height covering both blocks
                    new_w = (block['x_pdf'] + block['w_pdf']) - prev['x_pdf']
                    new_h = max(prev['y_pdf'] + prev['h_pdf'], block['y_pdf'] + block['h_pdf']) - new_y
                    new_prob = (prev['prob'] + block['prob']) / 2.0
                    
                    merged_line[-1] = {
                        'x_pdf': new_x,
                        'y_pdf': new_y,
                        'w_pdf': new_w,
                        'h_pdf': new_h,
                        'text': new_text,
                        'prob': new_prob
                    }
                else:
                    merged_line.append(block)
                    
        sorted_flat.extend(merged_line)
        
    return sorted_flat

def create_searchable_pdf_tesseract(input_pdf_path, output_pdf_path, tesseract_dir):
    """
    Generates a searchable PDF from a scanned PDF using PyMuPDF's Tesseract bindings.
    Detects tables using img2table and overlays cell border vectors onto the page.
    """
    print(f"[OCR] Running Tesseract OCR (Fast) on '{os.path.basename(input_pdf_path)}'...")
    
    # Set environment variable for Tesseract to find tessdata
    tessdata_path = os.path.join(tesseract_dir, "tessdata")
    os.environ["TESSDATA_PREFIX"] = tessdata_path
    
    doc = fitz.open(input_pdf_path)
    output_doc = fitz.open()
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        
        # Render page to high-res image (300 DPI)
        zoom = 300 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Remove alpha channel if present
        if pix.alpha:
            pix = fitz.Pixmap(pix, 0)
            
        # Run Tesseract OCR and get page as PDF bytes
        try:
            page_pdf_bytes = pix.pdfocr_tobytes(language="eng", tessdata=tessdata_path)
            page_pdf = fitz.open("pdf", page_pdf_bytes)
            
            # Detect tables on the page using img2table
            try:
                img_bytes = pix.tobytes("png")
                img_doc = TableImage(src=img_bytes)
                extracted_tables = img_doc.extract_tables(implicit_rows=True, implicit_columns=True, borderless_tables=True)
                
                if extracted_tables:
                    print(f"[OCR] Tesseract page {page_idx + 1}: detected {len(extracted_tables)} table(s)")
                    tess_page = page_pdf[0]
                    scale_x = tess_page.rect.width / pix.width
                    scale_y = tess_page.rect.height / pix.height
                    
                    for table in extracted_tables:
                        for row in table.content.values():
                            for cell in row:
                                cx1 = cell.bbox.x1 * scale_x
                                cy1 = cell.bbox.y1 * scale_y
                                cx2 = cell.bbox.x2 * scale_x
                                cy2 = cell.bbox.y2 * scale_y
                                rect = fitz.Rect(cx1, cy1, cx2, cy2)
                                tess_page.draw_rect(rect, color=(0, 0, 0), width=0.5)
            except Exception as table_err:
                print(f"[Warning] Tesseract table drawing failed on page {page_idx + 1}: {table_err}")
                
            output_doc.insert_pdf(page_pdf)
            page_pdf.close()
        except Exception as e:
            print(f"[Error] Tesseract OCR failed on page {page_idx + 1}: {e}")
            raise e
            
    output_doc.save(output_pdf_path)
    output_doc.close()
    doc.close()
    print(f"[OCR] Tesseract OCR completed. Saved searchable PDF to '{os.path.basename(output_pdf_path)}'.")

def create_searchable_pdf_easyocr(input_pdf_path, output_pdf_path):
    """
    Generates a searchable PDF from a scanned PDF using EasyOCR and PyMuPDF.
    Detects text, filters low-confidence noise, sorts text blocks into reading order,
    scales coordinates, overlays text invisibly, draws detected table cell borders, and creates links.
    """
    print(f"[OCR] Running EasyOCR (High Accuracy, Offline) on '{os.path.basename(input_pdf_path)}'...")
    
    # Lazy initialization of EasyOCR reader to save memory if not needed
    reader = easyocr.Reader(['en'], gpu=True) # Will automatically fall back to CPU if no GPU
    
    doc = fitz.open(input_pdf_path)
    output_doc = fitz.open()
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        print(f"[OCR] Processing page {page_idx + 1}/{len(doc)}...")
        
        # Render page to image at 300 DPI
        zoom = 300 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        
        # Run EasyOCR
        # Results is a list of: [([x_tl, y_tl], [x_tr, y_tr], [x_br, y_br], [x_bl, y_bl]), text, confidence]
        results = reader.readtext(img_bytes)
        
        # Create a new blank page with same dimensions as original
        new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
        
        # Draw the original page image onto the new page
        new_page.insert_image(new_page.rect, pixmap=pix)
        
        # Page dimensions in points
        w_points = page.rect.width
        h_points = page.rect.height
        
        # Image dimensions in pixels
        w_pixels = pix.width
        h_pixels = pix.height
        
        # Scale factors to convert pixels to points
        scale_x = w_points / w_pixels
        scale_y = h_points / h_pixels
        
        # Run table detection
        try:
            img_doc = TableImage(src=img_bytes)
            extracted_tables = img_doc.extract_tables(implicit_rows=True, implicit_columns=True, borderless_tables=True)
            if extracted_tables:
                print(f"[OCR] Page {page_idx + 1}: detected {len(extracted_tables)} table(s)")
                for table in extracted_tables:
                    for row in table.content.values():
                        for cell in row:
                            cx1 = cell.bbox.x1 * scale_x
                            cy1 = cell.bbox.y1 * scale_y
                            cx2 = cell.bbox.x2 * scale_x
                            cy2 = cell.bbox.y2 * scale_y
                            rect = fitz.Rect(cx1, cy1, cx2, cy2)
                            new_page.draw_rect(rect, color=(0, 0, 0), width=0.5)
        except Exception as table_err:
            print(f"[Warning] Table detection failed on page {page_idx + 1}: {table_err}")
            
        # Collect detected text blocks
        blocks = []
        for (bbox, text, prob) in results:
            text = text.strip()
            # Ignore empty strings and low confidence noise (like signature scribbles)
            if not text or prob < 0.15:
                continue
                
            tl, tr, br, bl = bbox
            x_pdf = tl[0] * scale_x
            y_pdf = tl[1] * scale_y
            
            w_pdf = (tr[0] - tl[0]) * scale_x
            h_pdf = (bl[1] - tl[1]) * scale_y
            
            blocks.append({
                'x_pdf': x_pdf,
                'y_pdf': y_pdf,
                'w_pdf': w_pdf,
                'h_pdf': h_pdf,
                'text': text,
                'prob': prob
            })
            
        # Sort text blocks line-by-line (top-to-bottom, left-to-right) for correct reading order
        sorted_blocks = sort_text_blocks(blocks)
        
        # Overlay the text layer (invisible, render_mode=3)
        for block in sorted_blocks:
            x_pdf = block['x_pdf']
            y_pdf = block['y_pdf']
            w_pdf = block['w_pdf']
            h_pdf = block['h_pdf']
            text = block['text']
            
            # Estimate font size based on bounding box height (using a realistic em-height factor of 0.75)
            font_size_h = max(1.0, h_pdf * 0.75)
            
            # Adjust font size if the text width exceeds the bounding box width.
            # We scale the font size down to fit the bounding box, but set a minimum cap of 6.0pt
            # to ensure text doesn't become illegibly tiny.
            try:
                w_calc = fitz.get_text_length(text, fontname="helv", fontsize=font_size_h)
                if w_calc > 0 and w_calc > w_pdf:
                    font_size_w = font_size_h * (w_pdf / w_calc)
                    font_size = max(6.0, min(font_size_h, font_size_w))
                else:
                    font_size = font_size_h
            except Exception:
                font_size = font_size_h

            
            # Align text to the baseline (approx 80% down the bounding box)
            baseline_y = y_pdf + (h_pdf * 0.8)
            
            # Insert text invisibly (render_mode=3)
            # Use default Helvetica font (or standard sans-serif)
            try:
                new_page.insert_text(
                    fitz.Point(x_pdf, baseline_y),
                    text,
                    fontsize=font_size,
                    fontname="helv",
                    render_mode=3,
                    color=(0, 0, 0)
                )
            except Exception as e:
                pass
            
            # Check if this text block looks like a URL
            if URL_PATTERN.match(text):
                url = text
                if url.startswith("www."):
                    url = "http://" + url
                
                rect = fitz.Rect(x_pdf, y_pdf, x_pdf + w_pdf, y_pdf + h_pdf)
                try:
                    new_page.insert_link({
                        "kind": fitz.LINK_URI,
                        "from": rect,
                        "uri": url
                    })
                    print(f"[OCR] Inserted hyperlink for URL: {url}")
                except Exception as e:
                    pass
                    
    output_doc.save(output_pdf_path)
    output_doc.close()
    doc.close()
    print(f"[OCR] EasyOCR completed. Saved searchable PDF to '{os.path.basename(output_pdf_path)}'.")

def make_searchable_pdf(input_pdf_path, output_pdf_path):
    """
    Main entry point for OCR: checks for Tesseract, uses it if available,
    otherwise falls back to EasyOCR to generate a searchable PDF.
    """
    tesseract_dir = get_tesseract_path()
    if tesseract_dir:
        print(f"[Info] Tesseract OCR installation found at: {tesseract_dir}")
        try:
            create_searchable_pdf_tesseract(input_pdf_path, output_pdf_path, tesseract_dir)
            return True
        except Exception as e:
            print(f"[Warning] Tesseract OCR failed: {e}. Falling back to EasyOCR...")
            
    print("[Info] Tesseract OCR not found. Using EasyOCR fallback.")
    try:
        create_searchable_pdf_easyocr(input_pdf_path, output_pdf_path)
        return True
    except Exception as e:
        print(f"[Error] EasyOCR failed: {e}")
        return False
