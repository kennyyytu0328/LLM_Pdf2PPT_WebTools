
from pptx import Presentation
from pptx.util import Pt, Cm, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
import io

# XML anchor attribute name constant
_ANCHOR_ATTR = qn('a:anchor')

class PPTGenerator:
    def __init__(self):
        self.prs = Presentation()
        # Remove default empty slide
        if len(self.prs.slides) > 0:
            # python-pptx starts with 0 slides by default if using default template? 
            # Actually standard Presentation() has 0 slides.
            pass

    def add_slide(self, page_data):
        # 1. Configure slide dimensions
        # PyMuPDF uses points usually (1/72 inch). PPTX uses EMU (1/914400 inch).
        # conversion: 1 point = 12700 EMU.
        width_pt = page_data["width"]
        height_pt = page_data["height"]
        
        self.prs.slide_width = int(width_pt * 12700)
        self.prs.slide_height = int(height_pt * 12700)
        
        # 2. Add blank slide
        blank_slide_layout = self.prs.slide_layouts[6] # 6 is usually "Blank"
        slide = self.prs.slides.add_slide(blank_slide_layout)
        
        # 3. First add text boxes BEFORE the background
        # This ensures proper z-ordering
        text_boxes = []
        for block in page_data["text_blocks"]:
            text = block["text"]
            x0, y0, x1, y1 = block["bbox"]
            font_size = block["size"]
            color_int = block["color"]
            bg_color = block.get("bg_color")  # Optional background fill (R, G, B)
            vertical_align = block.get("vertical_align", "top")  # top, center, bottom

            # Convert coordinates (1 point = 12700 EMU)
            x = int(x0 * 12700)
            y = int(y0 * 12700)
            w = int((x1 - x0) * 12700)
            h = int((y1 - y0) * 12700)

            # Avoid negative width/height
            if w <= 0: w = 10000
            if h <= 0: h = 10000

            textbox = slide.shapes.add_textbox(x, y, w, h)
            tf = textbox.text_frame

            # Enable word wrap for better text fitting
            # This allows iterative fitting approach to work
            tf.word_wrap = True

            # Set small margins to allow padding from bbox expansion to work
            # These internal margins provide a small buffer inside the box
            margin_val = Pt(1)  # 1pt internal margin
            tf.margin_left = margin_val
            tf.margin_right = margin_val
            tf.margin_top = margin_val
            tf.margin_bottom = margin_val

            # Set vertical alignment based on text block properties
            # VLM bbox y-coordinate often represents top of text, but text
            # baseline is typically near the bottom, so CENTER works better
            # Access the underlying XML element to set anchor
            tx_body = tf._txBody
            body_pr = tx_body.bodyPr
            if vertical_align == "center":
                body_pr.set(_ANCHOR_ATTR, 'ctr')
            elif vertical_align == "bottom":
                body_pr.set(_ANCHOR_ATTR, 'b')
            else:
                body_pr.set(_ANCHOR_ATTR, 't')

            # Apply background fill if available (for OCR mode)
            # This creates an opaque overlay that covers the original text
            if bg_color:
                fill = textbox.fill
                fill.solid()
                fill.fore_color.rgb = RGBColor(bg_color[0], bg_color[1], bg_color[2])

            p = tf.paragraphs[0]
            p.text = text
            p.font.size = Pt(font_size)

            # Color conversion
            # PyMuPDF color is sRGB int.
            # python-pptx RGBColor takes R, G, B
            if isinstance(color_int, int):
                R = (color_int >> 16) & 255
                G = (color_int >> 8) & 255
                B = color_int & 255
            else:
                R, G, B = 0, 0, 0  # Default to black for OCR
            p.font.color.rgb = RGBColor(R, G, B)

            text_boxes.append(textbox)
        
        # 4. Now add background image
        image_stream = io.BytesIO(page_data["background_image"])
        pic = slide.shapes.add_picture(
            image_stream, 
            0, 0, 
            self.prs.slide_width, 
            self.prs.slide_height
        )
        
        # 5. CRITICAL: Move background to the back
        # Access the underlying XML and reorder
        slide_part = slide._element
        shape_tree = slide_part.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}spTree')
        
        # Get the picture element (last added)
        pic_element = pic._element
        
        # Remove it from current position
        shape_tree.remove(pic_element)
        
        # Insert it at position 0 (behind everything)
        # Note: first child is usually nvGrpSpPr and grpSpPr, so insert at index 2
        shape_tree.insert(2, pic_element)

    def save(self) -> io.BytesIO:
        output = io.BytesIO()
        self.prs.save(output)
        output.seek(0)
        return output
