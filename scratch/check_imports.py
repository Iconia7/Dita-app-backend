import sys
import os

# Add the project path to sys.path
sys.path.append(os.getcwd())

try:
    import docx
    print(f"SUCCESS: docx version: {docx.__version__}")
except ImportError as e:
    print(f"ERROR: docx import failed: {e}")
except Exception as e:
    print(f"ERROR: Unexpected error during docx import: {e}")

try:
    from config.utils import process_nursing_exam_docx
    print("SUCCESS: process_nursing_exam_docx imported successfully")
except ImportError as e:
    print(f"ERROR: from config.utils import failed: {e}")
except Exception as e:
    print(f"ERROR: Error importing process_nursing_exam_docx: {e}")
