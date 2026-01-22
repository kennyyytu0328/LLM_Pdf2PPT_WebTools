
import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print("Attempting to import rapidocr_onnxruntime...")

try:
    from rapidocr_onnxruntime import RapidOCR
    print("SUCCESS: RapidOCR imported successfully.")
    ocr = RapidOCR()
    print("SUCCESS: RapidOCR initialized.")
    
except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except Exception as e:
    print(f"FAILURE: Exception: {e}")
    import traceback
    traceback.print_exc()

print("\nChecking installed packages matching 'rapid':")
try:
    import importlib.metadata
    dists = importlib.metadata.distributions()
    for dist in dists:
        if "rapid" in dist.metadata["Name"].lower():
            print(f"- {dist.metadata['Name']} ({dist.version})")
except Exception as e:
    print(f"Error checking packages: {e}")
