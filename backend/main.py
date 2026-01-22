
# CRITICAL: Set environment variables BEFORE importing PaddlePaddle
import os
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["MKLDNN_CACHE_CAPACITY"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"  # Disable PIR API that causes the error

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
from pdf_processor import PDFProcessor
from ppt_generator import PPTGenerator

app = FastAPI(title="PDF to PPT Converter")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/convert")
async def convert_pdf_to_ppt(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")
    
    try:
        content = await file.read()
        
        # Initialize processors
        pdf_proc = PDFProcessor(content)
        ppt_gen = PPTGenerator()
        
        # Iterate through all pages
        # PyMuPDF doc is iterable or we use len
        page_count = len(pdf_proc.doc)
        
        for i in range(page_count):
            page_data = pdf_proc.process_page(i)
            ppt_gen.add_slide(page_data)
            
        pdf_proc.close()
        
        # Save PPT
        output_io = ppt_gen.save()
        
        filename = file.filename.replace(".pdf", ".pptx")
        
        # Return as downloadable file
        return StreamingResponse(
            output_io,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
