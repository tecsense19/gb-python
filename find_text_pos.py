import os, sys
from pathlib import Path

# Add local 'lib' directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(BASE_DIR, 'lib')
if os.path.exists(LIB_PATH) and LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

from pypdf import PdfReader

if __name__ == "__main__":
    reader = PdfReader("fw9_new.pdf")
    with open("text_dump.txt", "w", encoding="utf-8") as f:
        for page_idx, page in enumerate(reader.pages):
            f.write(f"--- PAGE {page_idx} ---\n")
            def visitor_body(text, cm, tm, font_dict, font_size):
                if text.strip():
                    f.write(f"'{text.strip()}' at TM={tm}\n")
            page.extract_text(visitor_text=visitor_body)
    print("Dumped to text_dump.txt")
