
import fitz  # PyMuPDF
from pptx.util import Pt, Cm
from typing import List, Dict, Tuple
import io
import os
import base64
import json
import numpy as np
import requests

# --- LLM OCR 設定 ---
API_BASE_URL = "http://192.168.50.53:1234/v1"
API_KEY = "lm-studio"
MODEL_ID = "qwen3-vl-30b-a3b-instruct"

# --- RapidOCR for positioning ---
try:
    from rapidocr_onnxruntime import RapidOCR
    _ocr_engine = None
    def get_ocr_engine():
        global _ocr_engine
        if _ocr_engine is None:
            print("Initializing RapidOCR engine...")
            _ocr_engine = RapidOCR()
        return _ocr_engine
    HAS_RAPID_OCR = True
except ImportError:
    HAS_RAPID_OCR = False
    print("Warning: RapidOCR not installed. Hybrid OCR will not be available.")


def sample_background_color(img_np: np.ndarray, bbox: Tuple[float, float, float, float], scale: float) -> Tuple[int, int, int]:
    """Sample the background color around a text bounding box.

    Uses an expanded sampling region to better capture the true background,
    especially useful when VLM bboxes are tightly fit to text.
    """
    x0, y0, x1, y1 = bbox
    box_w = x1 - x0
    box_h = y1 - y0

    # Expand sampling region by 10% to get better background samples
    sample_expand_x = box_w * 0.10
    sample_expand_y = box_h * 0.10

    sx0 = (x0 - sample_expand_x) * scale
    sy0 = (y0 - sample_expand_y) * scale
    sx1 = (x1 + sample_expand_x) * scale
    sy1 = (y1 + sample_expand_y) * scale

    h, w = img_np.shape[:2]
    ix0 = max(0, min(int(sx0), w-1))
    iy0 = max(0, min(int(sy0), h-1))
    ix1 = max(0, min(int(sx1), w-1))
    iy1 = max(0, min(int(sy1), h-1))

    samples = []
    # Sample from expanded edges (more likely to be pure background)
    if iy0 < h: samples.extend(img_np[iy0, ix0:ix1+1].tolist())
    if iy1 < h: samples.extend(img_np[iy1, ix0:ix1+1].tolist())
    if ix0 < w: samples.extend(img_np[iy0:iy1+1, ix0].tolist())
    if ix1 < w: samples.extend(img_np[iy0:iy1+1, ix1].tolist())

    if not samples: return (255, 255, 255)
    samples = np.array(samples)
    if samples.ndim == 1:
        avg = int(np.mean(samples))
        return (avg, avg, avg)
    else:
        avg = np.mean(samples, axis=0).astype(int)
        return (int(avg[0]), int(avg[1]), int(avg[2]))


def expand_bbox_with_padding(bbox: Tuple[float, float, float, float],
                              page_width: float,
                              page_height: float,
                              h_pad_pct: float = 0.03,
                              v_pad_top_pct: float = 0.02,
                              v_pad_bottom_pct: float = 0.01) -> Tuple[float, float, float, float]:
    """Expand bounding box with padding to ensure complete text coverage.

    VLM-generated bboxes are often tight-fitting "minimum bounding rectangles".
    Adding padding prevents edge artifacts when overlaying text.

    Args:
        bbox: Original (x0, y0, x1, y1) coordinates
        page_width: Page width for boundary clamping
        page_height: Page height for boundary clamping
        h_pad_pct: Horizontal padding percentage (applied to width, both sides)
        v_pad_top_pct: Vertical padding for top
        v_pad_bottom_pct: Vertical padding for bottom

    Returns:
        Expanded bbox tuple
    """
    x0, y0, x1, y1 = bbox
    box_w = x1 - x0
    box_h = y1 - y0

    # Calculate padding amounts
    h_pad = box_w * h_pad_pct
    v_pad_top = box_h * v_pad_top_pct
    v_pad_bottom = box_h * v_pad_bottom_pct

    # Apply padding with boundary clamping
    new_x0 = max(0, x0 - h_pad)
    new_y0 = max(0, y0 - v_pad_top)
    new_x1 = min(page_width, x1 + h_pad)
    new_y1 = min(page_height, y1 + v_pad_bottom)

    return (new_x0, new_y0, new_x1, new_y1)


def estimate_font_size_iterative(text: str,
                                  box_width: float,
                                  box_height: float,
                                  min_size: float = 8,
                                  max_size: float = 72) -> float:
    """Estimate optimal font size using iterative fitting approach.

    Instead of simple linear calculation (h * 0.7), this considers:
    - Text length and box width ratio
    - CJK vs Latin character width differences
    - Ascender/descender proportions

    Args:
        text: The text content
        box_width: Available width in points
        box_height: Available height in points
        min_size: Minimum allowed font size
        max_size: Maximum allowed font size

    Returns:
        Estimated font size in points
    """
    if not text.strip():
        return min_size

    # Count CJK characters (wider glyphs)
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or
                   '\u3040' <= c <= '\u30ff' or '\uac00' <= c <= '\ud7af')
    latin_count = len(text) - cjk_count

    # Estimate average character width factor
    # CJK: ~1.0 em width, Latin: ~0.5 em width (average)
    effective_char_count = cjk_count * 1.0 + latin_count * 0.55

    if effective_char_count == 0:
        effective_char_count = len(text) * 0.55

    # Height-based estimation (considering typical ascender/descender)
    # Standard font: ~80% of em-height is visible cap height
    height_based_size = box_height * 0.85

    # Width-based estimation
    if effective_char_count > 0:
        width_based_size = box_width / effective_char_count
    else:
        width_based_size = height_based_size

    # Take the smaller of the two (ensure text fits both dimensions)
    estimated_size = min(height_based_size, width_based_size)

    # Apply bounds
    return max(min_size, min(estimated_size, max_size))


class PDFProcessor:
    def __init__(self, pdf_bytes: bytes):
        self.doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    def _ocr_with_rapidocr(self, img_np: np.ndarray, scale_factor: float) -> List[Dict]:
        """Use RapidOCR to get text blocks with precise positions."""
        if not HAS_RAPID_OCR:
            return []
        
        ocr = get_ocr_engine()
        result, _ = ocr(img_np)
        
        blocks = []
        if result:
            for item in result:
                box = item[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text = item[1]
                try:
                    confidence = float(item[2]) if len(item) > 2 else 1.0
                except:
                    confidence = 0.0
                
                if text.strip() and confidence > 0.3:
                    x_coords = [p[0] for p in box]
                    y_coords = [p[1] for p in box]
                    x0 = min(x_coords) / scale_factor
                    y0 = min(y_coords) / scale_factor
                    x1 = max(x_coords) / scale_factor
                    y1 = max(y_coords) / scale_factor
                    
                    blocks.append({
                        "ocr_text": text,
                        "bbox": (x0, y0, x1, y1),
                        "confidence": confidence
                    })
        
        print(f"RapidOCR detected {len(blocks)} text blocks.")
        return blocks

    def _refine_text_with_llm(self, base64_img: str, ocr_blocks: List[Dict],
                               img_width: int = None, img_height: int = None) -> List[Dict]:
        """Send image + OCR results to LLM for text correction and bbox refinement.

        Enhanced prompt strategy to get more precise bounding boxes from VLM.
        """
        if not ocr_blocks:
            return []

        # Build a summary of OCR results for LLM with bbox info
        ocr_summary_lines = []
        for i, b in enumerate(ocr_blocks):
            bbox = b['bbox']
            ocr_summary_lines.append(
                f"- Block {i+1}: \"{b['ocr_text']}\" at approx. region "
                f"[x:{bbox[0]:.1f}, y:{bbox[1]:.1f}, w:{bbox[2]-bbox[0]:.1f}, h:{bbox[3]-bbox[1]:.1f}]"
            )
        ocr_summary = "\n".join(ocr_summary_lines)

        # Enhanced prompt with coordinate refinement request
        prompt = f"""You are a precise text extraction assistant for slide conversion.
I have OCR results that may have character errors and imprecise bounding boxes.

OCR Results (may contain errors):
{ocr_summary}

**Your Task:**
1. CORRECT any character recognition errors by examining the image
2. REFINE the bounding box coordinates to FULLY CONTAIN the text background area
   - The bbox should include ALL pixels of the text background, not just the text itself
   - Add small margins to ensure complete coverage

Return a JSON array in this EXACT format:
[
  {{
    "id": 1,
    "corrected_text": "The corrected text",
    "bbox_adjustment": {{"expand_left": 0, "expand_right": 0, "expand_top": 0, "expand_bottom": 0}}
  }}
]

**Guidelines for bbox_adjustment (in points/pixels):**
- expand_left/right: Add 2-5 units if text appears cropped horizontally
- expand_top: Add 1-3 units if ascenders (like 'b', 'd', 'h') appear cropped
- expand_bottom: Add 1-2 units if descenders (like 'g', 'p', 'y') appear cropped
- Use 0 if the bbox already fully contains the text background

**IMPORTANT:**
- Keep the same number of blocks as input
- Do NOT merge or split blocks
- Return ONLY the JSON array, no other text
- If a block looks correct, return it with corrected_text unchanged and all adjustments as 0"""

        payload = {
            "model": MODEL_ID,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}}
                    ]
                }
            ],
            "temperature": 0
        }

        try:
            print("Sending to LLM for text refinement and bbox adjustment...")
            response = requests.post(f"{API_BASE_URL}/chat/completions", json=payload, timeout=90)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']

            # Clean up JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            corrections = json.loads(content)

            # Apply corrections and bbox adjustments
            for correction in corrections:
                idx = correction.get("id", 0) - 1  # 1-indexed to 0-indexed
                if 0 <= idx < len(ocr_blocks):
                    corrected = correction.get("corrected_text", "")
                    if corrected:
                        ocr_blocks[idx]["text"] = corrected

                    # Apply bbox adjustments from VLM
                    adj = correction.get("bbox_adjustment", {})
                    if adj:
                        x0, y0, x1, y1 = ocr_blocks[idx]["bbox"]
                        x0 -= adj.get("expand_left", 0)
                        y0 -= adj.get("expand_top", 0)
                        x1 += adj.get("expand_right", 0)
                        y1 += adj.get("expand_bottom", 0)
                        ocr_blocks[idx]["bbox"] = (x0, y0, x1, y1)
                        ocr_blocks[idx]["vlm_adjusted"] = True

            # For blocks without LLM correction, use original OCR text
            for block in ocr_blocks:
                if "text" not in block:
                    block["text"] = block["ocr_text"]

            adjusted_count = sum(1 for b in ocr_blocks if b.get("vlm_adjusted", False))
            print(f"LLM refined {len(corrections)} text blocks, adjusted {adjusted_count} bboxes.")
            return ocr_blocks

        except Exception as e:
            print(f"LLM refinement failed: {str(e)}. Using OCR text as-is.")
            for block in ocr_blocks:
                block["text"] = block["ocr_text"]
            return ocr_blocks

    def _extract_text_hybrid(self, page, bg_img_np: np.ndarray, bg_scale: float) -> List[Dict]:
        """Hybrid approach: RapidOCR for positions + LLM for text correction."""
        page_width = page.rect.width
        page_height = page.rect.height

        # Step 1: Get positions from RapidOCR
        ocr_blocks = self._ocr_with_rapidocr(bg_img_np, bg_scale)

        if not ocr_blocks:
            print("No text detected by RapidOCR.")
            return []

        # Step 2: Prepare image for LLM
        from PIL import Image
        img = Image.fromarray(bg_img_np)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        base64_img = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Step 3: Send to LLM for text refinement and bbox adjustment
        img_h, img_w = bg_img_np.shape[:2]
        refined_blocks = self._refine_text_with_llm(base64_img, ocr_blocks, img_w, img_h)

        # Step 4: Build final text_blocks with padding and improved font sizing
        text_blocks = []
        for block in refined_blocks:
            original_bbox = block["bbox"]

            # Apply padding to bbox for better coverage
            padded_bbox = expand_bbox_with_padding(
                original_bbox,
                page_width,
                page_height,
                h_pad_pct=0.03,      # 3% horizontal padding each side
                v_pad_top_pct=0.02,  # 2% top padding
                v_pad_bottom_pct=0.01  # 1% bottom padding
            )

            x0, y0, x1, y1 = padded_bbox
            box_w = x1 - x0
            box_h = y1 - y0

            # Sample background color from ORIGINAL bbox area (before padding)
            # to get accurate background, not from padded region
            bg_color = sample_background_color(bg_img_np, original_bbox, bg_scale)

            # Improved font size estimation using iterative approach
            final_size = estimate_font_size_iterative(
                block["text"],
                box_w,
                box_h,
                min_size=8,
                max_size=72
            )

            text_blocks.append({
                "text": block["text"],
                "bbox": padded_bbox,
                "original_bbox": original_bbox,  # Keep original for reference
                "size": final_size,
                "font": "Arial",
                "color": 0,
                "origin": (x0, y0 + box_h * 0.8),
                "bg_color": bg_color,
                "vertical_align": "center"  # New: specify vertical alignment
            })

        return text_blocks

    def process_page(self, page_num: int) -> Dict:
        page = self.doc.load_page(page_num)
        
        # 1. Try to extract text normally
        text_blocks = []
        page_dict = page.get_text("dict")
        
        for block in page_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["text"].strip():
                            text_blocks.append({
                                "text": span["text"],
                                "bbox": span["bbox"],
                                "size": span["size"],
                                "font": span["font"],
                                "color": span["color"],
                                "origin": span["origin"],
                                "bg_color": None
                            })

        # 2. If no text found, use hybrid OCR
        use_ocr = len(text_blocks) == 0
        
        # 3. Render background image (2x)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("png")
        
        if use_ocr:
            print(f"Page {page_num + 1}: Using Hybrid OCR (RapidOCR + LLM)...")
            from PIL import Image
            bg_img = Image.open(io.BytesIO(img_data))
            bg_img_np = np.array(bg_img)
            text_blocks = self._extract_text_hybrid(page, bg_img_np, 2.0)
        else:
            # Native text: redact and re-render
            for block in text_blocks:
                page.add_redact_annot(block["bbox"], fill=False)
            page.apply_redactions()
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("png")

        return {
            "width": page.rect.width,
            "height": page.rect.height,
            "text_blocks": text_blocks,
            "background_image": img_data,
            "used_ocr": use_ocr
        }

    def close(self):
        self.doc.close()
