# PDF to Editable PowerPoint (Hybrid OCR Edition)

Convert PDF presentations into fully editable PowerPoint (.pptx) files while preserving background design. Uses advanced Hybrid OCR combining RapidOCR for positioning and Qwen-VL LLM for intelligent text recognition.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Node.js 18.0+](https://img.shields.io/badge/node-18.0%2B-green)](https://nodejs.org/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)

## Features

✨ **Background Preservation**
Maintains all visual elements from the original PDF—colors, gradients, logos, and design patterns.

🎯 **Hybrid OCR System**
Combines RapidOCR for pixel-perfect text positioning with Qwen-VL LLM for context-aware text correction.

🔤 **Smart Text Recognition**
Handles programming code, Chinese/Japanese text, complex layouts, and special characters with high accuracy.

🎨 **Intelligent Background Filling**
Automatically samples background colors and creates solid overlays that naturally mask original text.

🖥️ **Modern Web Interface**
Premium glassmorphism-styled drag-and-drop UI for seamless file uploads and conversion.

⚡ **GPU Optimized**
Fully compatible with Linux GPU servers for high-performance batch processing.

## Quick Start

### Prerequisites
- Python 3.10+ with pip
- Node.js 18.0+
- Modern web browser (Chrome, Firefox, Edge)
- LM Studio running with a Qwen-VL model

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd PDF_to_PPT_webtools

# 2. Backend setup (Python)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install rapidocr_onnxruntime onnxruntime

# 3. Configure LM Studio connection
# Edit backend/pdf_processor.py and update:
# - API_BASE_URL = "http://YOUR_SERVER_IP:1234/v1"
# - MODEL_ID = "qwen3-vl-30b-a3b-instruct"

# 4. Frontend setup (Node.js)
cd frontend
npm install
cd ..

# 5. Run the application
# Terminal 1: Backend
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev -- --host
```

Open http://localhost:5173 in your browser and start converting!

## System Requirements

### General
- **Python 3.10+**
- **Node.js 18.0+** (Required for Vite 5+)
- **Modern Web Browser** (Chrome, Firefox, Edge)

### AI Backend (LM Studio)
- **LM Studio** installed and running
- **Supported Models:**
  - `qwen2-vl-7b-instruct` (8GB+ VRAM)
  - `qwen3-vl-30b-a3b-instruct` (24GB+ VRAM, higher accuracy)
  - Other Qwen-VL variants with compatible API
- **Server Configuration:** Local Server mode enabled on port 1234
- **GPU:** Minimum 8GB VRAM (7B models), 24GB+ recommended (30B models)

## How It Works

The tool uses a sophisticated 5-phase workflow:

### Phase 1: Physical Positioning (RapidOCR)
RapidOCR scans the page image to detect every text block's exact pixel coordinates.

### Phase 2: Semantic Refinement (Qwen-VL LLM)
The LLM corrects OCR errors and refines bounding boxes by analyzing the image context.

### Phase 3: Smart Background Filling
Samples background colors around text regions and applies solid overlays to mask original PDF text.

### Phase 4: Advanced Font Sizing
Intelligently estimates font sizes considering character width, height constraints, and typography.

### Phase 5: PowerPoint Generation
Assembles the final slide with proper z-ordering, text alignment, and formatting.

**For detailed technical documentation**, see [USER_MANUAL.md](USER_MANUAL.md)

## Configuration

Edit `backend/pdf_processor.py` to configure your LM Studio connection:

```python
# --- LLM OCR Settings ---
API_BASE_URL = "http://192.168.50.53:1234/v1"  # Your LM Studio server IP
API_KEY = "lm-studio"
MODEL_ID = "qwen3-vl-30b-a3b-instruct"          # Your loaded model ID
```

### Key Settings
- **API_BASE_URL**: Your LM Studio server address
- **MODEL_ID**: Must match a model loaded in LM Studio
- **Timeout**: 90 seconds (adjust for large models)

## Usage

### Web Interface
1. Open http://localhost:5173
2. Drag and drop a PDF file (or click to browse)
3. Wait for conversion to complete
4. Download the .pptx file
5. Open in PowerPoint and edit freely

### Supported Input
- PDF presentations (single or multi-page)
- NotebookLM exports (optimal)
- Scanned PDFs (with OCR)
- High-resolution layouts

### Output
- Fully editable PowerPoint (.pptx) files
- Preserved background design
- Extracted text as selectable text boxes
- Compatible with Microsoft Office, Google Slides, LibreOffice

## Troubleshooting

### Common Issues

**"LLM OCR Failed" or Timeout**
- Ensure LM Studio Server is running (`http://server-ip:1234/v1` is accessible)
- Check network connectivity to LM Studio host
- Verify MODEL_ID matches a loaded model in LM Studio
- Increase timeout for large models (24GB+)

**"ModuleNotFoundError: No module named 'uvicorn'"**
- Activate virtual environment: `source .venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

**Node.js SyntaxError**
- Upgrade to Node.js 18+: `nvm install 18`

**Text extraction issues**
- Ensure RapidOCR is installed: `pip install rapidocr_onnxruntime`
- Check if PDF is scanned or has selectable text
- Verify image quality (low-resolution PDFs may fail)

For more troubleshooting tips, see [USER_MANUAL.md#troubleshooting-linux-specific](USER_MANUAL.md#troubleshooting-linux-specific)

## Project Structure

```
PDF_to_PPT_webtools/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── pdf_processor.py     # OCR & text extraction
│   ├── ppt_generator.py     # PowerPoint generation
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── App.tsx          # Main app
│   │   └── main.tsx         # Entry point
│   ├── package.json         # Node dependencies
│   └── vite.config.ts       # Vite configuration
├── USER_MANUAL.md           # Detailed documentation
└── README.md                # This file
```

## Performance

- **Small PDFs (<10 pages):** ~30-60 seconds
- **Medium PDFs (10-50 pages):** ~2-5 minutes
- **Large PDFs (50+ pages):** Depends on GPU and model size

*Typical timing on RTX 4090 with 30B model*

## What Makes This Different

Most PDF-to-PPT tools struggle with:
- Precise text positioning
- Background preservation
- Character recognition accuracy
- Complex layouts

This tool solves these by:
1. Using **RapidOCR** for pixel-perfect positioning
2. Using **Qwen-VL LLM** for semantic understanding
3. Sampling actual background colors for natural overlays
4. Supporting CJK characters and code formatting
5. Maintaining PowerPoint editability

## Ideal Use Cases

- Converting NotebookLM-generated PDF presentations
- Batch processing research papers to editable slides
- Digitizing printed presentations
- Creating editable slide decks from generated PDFs
- Preserving document design while enabling editing

## Linux Deployment

For GPU servers running Linux, follow the detailed setup in [USER_MANUAL.md#linux-installation--setup](USER_MANUAL.md#linux-installation--setup)

## Requirements

See [requirements.txt](backend/requirements.txt) for complete Python dependencies.

Key packages:
- **FastAPI** - Web framework
- **python-pptx** - PowerPoint generation
- **PyMuPDF** - PDF processing
- **RapidOCR** - Text detection
- **Pillow** - Image handling

## License & Credits

This tool is optimized for **NotebookLM** exports and requires **LM Studio** for AI processing.

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [python-pptx](https://python-pptx.readthedocs.io/)
- [RapidOCR](https://github.com/RapidAI/RapidOCR)
- [Qwen-VL](https://github.com/QwenLM/Qwen-VL) via LM Studio

## Support & Feedback

For detailed documentation, troubleshooting, and advanced configuration, see [USER_MANUAL.md](USER_MANUAL.md)

## Author

Created for batch PDF presentation conversion with preserved backgrounds and editable text.

---

**Get Started:** Clone this repo, follow the Quick Start above, and convert your first PDF in minutes!
