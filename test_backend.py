
import fitz
from backend.pdf_processor import PDFProcessor
from backend.ppt_generator import PPTGenerator
import os

def create_dummy_pdf(filename="test.pdf"):
    doc = fitz.open()
    page = doc.new_page()
    
    # Draw a blue rectangle (background element)
    shape = page.new_shape()
    shape.draw_rect((50, 50, 200, 200))
    shape.finish(color=(1, 0, 0), fill=(0, 0, 1)) # Red border, Blue fill
    shape.commit()
    
    # Add text ON TOP
    page.insert_text((100, 100), "Hello World!", fontsize=24, color=(1, 1, 1)) # White text
    
    doc.save(filename)
    doc.close()
    return filename

def test_conversion():
    pdf_file = create_dummy_pdf()
    print(f"Created {pdf_file}")
    
    with open(pdf_file, "rb") as f:
        pdf_bytes = f.read()
        
    print("Processing PDF...")
    pdf_proc = PDFProcessor(pdf_bytes)
    ppt_gen = PPTGenerator()
    
    for i in range(len(pdf_proc.doc)):
        page_data = pdf_proc.process_page(i)
        ppt_gen.add_slide(page_data)
        
    pdf_proc.close()
    
    output = ppt_gen.save()
    with open("test_output.pptx", "wb") as f:
        f.write(output.read())
        
    print("Created test_output.pptx")
    
    # Verify file exists and has size
    if os.path.exists("test_output.pptx") and os.path.getsize("test_output.pptx") > 0:
        print("SUCCESS: PPTX generated.")
    else:
        print("FAILURE: PPTX not generated or empty.")

if __name__ == "__main__":
    test_conversion()
