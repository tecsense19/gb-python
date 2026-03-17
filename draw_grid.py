import os, sys
from pathlib import Path

# Add local 'lib' directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(BASE_DIR, 'lib')
if os.path.exists(LIB_PATH) and LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO

def draw_grid(pdf_path, output_path):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    for page_idx, page in enumerate(reader.pages):
        packet = BytesIO()
        can = canvas.Canvas(packet)
        can.setFont("Helvetica", 8)
        can.setStrokeColorRGB(0.8, 0.8, 0.8)
        can.setLineWidth(0.5)
        
        # Draw horizontal lines every 50 points
        for y in range(0, 800, 50):
            can.line(0, y, 612, y)
            can.drawString(5, y + 2, str(y))
            
        # Draw vertical lines every 50 points
        for x in range(0, 612, 50):
            can.line(x, 0, x, 792)
            can.drawString(x + 2, 5, str(x))
            
        # Draw a more fine grid at the bottom area (0-200)
        can.setStrokeColorRGB(1, 0, 0) # Red for fine grid
        for y in range(0, 200, 10):
            can.line(0, y, 612, y)
            if y % 50 != 0:
                can.drawString(5, y + 2, str(y))

        can.save()
        packet.seek(0)
        grid_reader = PdfReader(packet)
        page.merge_page(grid_reader.pages[0])
        writer.add_page(page)
        
    with open(output_path, "wb") as f:
        writer.write(f)

if __name__ == "__main__":
    draw_grid("fw9_new.pdf", "fw9_with_grid.pdf")
