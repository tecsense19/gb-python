#!/usr/bin/env python3
"""
fill_pdf.py — Fills IRS PDFs (XFA) and adds a digital signature image with a timestamp.
"""

import sys, json, re, os, datetime
from pathlib import Path

# Add local 'lib' directory to sys.path to ensure web server finds dependencies
lib_path = os.path.join(os.path.dirname(__file__), 'lib')
if os.path.exists(lib_path) and lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import NameObject, BooleanObject
from io import BytesIO

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
except ImportError:
    print("ERROR: Run: pip install reportlab", file=sys.stderr)
    sys.exit(1)

# Signature configuration (page coordinate mapping)
# x, y from bottom-left
# w, h is image size
# tx, ty is relative offset for text
SIGNATURE_MAP = {
    "w9":       {"page": 0, "x": 130, "y": 205, "w": 200, "h": 40, "dx": 350, "dy": -18},
    "w8i":      {"page": 0, "x": 90,  "y": 65,  "w": 180, "h": 40, "dx": 350, "dy": 0},
    "w8e":      {"page": 7, "x": 90,  "y": 110, "w": 180, "h": 40, "dx": 350, "dy": 0},
}

def fill_xfa(writer, fields: dict):
    try:
        acro = writer.root_object["/AcroForm"]
        # Ensure NeedAppearances is set
        acro.update({
            NameObject("/NeedAppearances"): BooleanObject(True)
        })
        
        xfa = acro["/XFA"]
    except Exception as e:
        print(f"WARNING: AcroForm or XFA not found: {e}", file=sys.stderr)
        return False

    datasets_obj = None
    if isinstance(xfa, list):
        for i in range(0, len(xfa), 2):
            if xfa[i] == 'datasets':
                datasets_obj = xfa[i + 1].get_object()
                break
    
    if datasets_obj is None:
        print("ERROR: datasets XFA object not found", file=sys.stderr)
        return False

    # Prepare normalized fields for XFA and AcroForm
    normalized_fields = {}
    
    for k, v in fields.items():
        # Handle c1_1 to c1_7 mapping
        # If user passes 'c1_2': 1, we map it to 'c1_1': 2
        match = re.match(r'^c1_([1-7])$', k)
        if match and (str(v) == '1' or v is True):
            normalized_fields['c1_1'] = match.group(1)
        else:
            normalized_fields[k] = v

    # 1. Update XFA XML
    xml = datasets_obj.get_data().decode('utf-8', errors='ignore')

    for tag, value in normalized_fields.items():
        safe = (str(value)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))
        
        # Robust regex: handle tags with attributes or line breaks
        # Pattern 1: <tag ... /> (self-closing)
        xml = re.sub(r'<' + re.escape(tag) + r'\b[^>]*?/>', f'<{tag}>{safe}</{tag}>', xml, flags=re.DOTALL)
        
        # Pattern 2: <tag ...>...</tag> (with content)
        xml = re.sub(r'<' + re.escape(tag) + r'\b[^>]*?>.*?</' + re.escape(tag) + r'\s*>',
                     f'<{tag}>{safe}</{tag}>', xml, flags=re.DOTALL)

    datasets_obj._data = xml.encode('utf-8')
    if '/Filter' in datasets_obj:
        del datasets_obj['/Filter']
    
    # 2. Fill AcroForm fields for better viewer compatibility
    acro_mapping = {}
    reader_fields = writer.get_fields()
    
    for k, v in normalized_fields.items():
        # Special case for checkboxes like c1_1 (numeric 1-7)
        if k == 'c1_1' and str(v).isdigit():
            val_int = int(v)
            if 1 <= val_int <= 7:
                idx = val_int - 1
                # Search for the checkbox field by suffix
                search_suffix = f"c1_1[{idx}]"
                for full_name in reader_fields.keys():
                    if full_name == search_suffix or full_name.endswith("." + search_suffix):
                        # For XFA checkboxes, setting the value to match the 'On' state
                        acro_mapping[full_name] = f"/{v}" 
        
        # Standard field mapping
        for full_name, field_obj in reader_fields.items():
            if full_name.endswith(f".{k}[0]") or full_name == k:
                # If it's a Checkbox/Button and the value implies it should be checked
                if field_obj.get('/FT') == '/Btn' and str(v).strip().lower() in ['1', 'yes', 'true', 'on']:
                    # Use the first available 'On' state, or default to '/1'
                    on_state = '/1'
                    try:
                        n_dict = field_obj.get('/AP', {}).get('/N', {})
                        keys = [key for key in n_dict.keys() if key != '/Off']
                        if keys:
                            on_state = keys[0]
                    except:
                        pass
                    acro_mapping[full_name] = on_state
                else:
                    acro_mapping[full_name] = v

    if acro_mapping:
        for page in writer.pages:
            writer.update_page_form_field_values(page, acro_mapping)
    
    return True

def add_signature(writer, signature_path, form_type):
    if not os.path.exists(signature_path):
        print(f"DEBUG fill_pdf: signature_path not found: {signature_path}")
        return
    
    print(f"DEBUG fill_pdf: Adding signature for {form_type} using {signature_path}")
    
    form_type_key = form_type.lower()
    if form_type_key not in SIGNATURE_MAP:
        print(f"DEBUG fill_pdf: No signature configuration for form type '{form_type}'")
        return
    
    config = SIGNATURE_MAP[form_type_key]
    page_idx = config["page"]
    
    if page_idx >= len(writer.pages):
        print(f"WARNING: Page {page_idx} not found in PDF", file=sys.stderr)
        return

    # Create overlay PDF with reportlab
    packet = BytesIO()
    can = canvas.Canvas(packet)
    
    # 1. Draw Image
    try:
        can.drawImage(signature_path, config["x"], config["y"], 
                     width=config["w"], height=config["h"], 
                     mask='auto')
    except Exception as e:
        print(f"ERROR: Failed to draw signature image: {e}", file=sys.stderr)
        return

    # 2. Draw Date
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    
    can.setFont("Helvetica", 10)
    can.setFillAlpha(1.0)
    # Use dx/dy if provided, else fallback to tx/ty
    dx = config.get("dx", config.get("tx", 0))
    dy = config.get("dy", config.get("ty", 0))
    can.drawString(config["x"] + dx, config["y"] + dy, now)
    
    can.save()
    packet.seek(0)
    
    overlay_reader = PdfReader(packet)
    overlay_page = overlay_reader.pages[0]
    
    # Merge overlay with original page
    target_page = writer.pages[page_idx]
    target_page.merge_page(overlay_page)
    print(f"DEBUG fill_pdf: Signature merged onto page {page_idx} at x={config['x']}, y={config['y']}")

def main():
    if len(sys.argv) < 4:
        print(f"Usage: python {sys.argv[0]} blank.pdf fields.json output.pdf [signature.png] [form_type]")
        sys.exit(1)

    blank_path = sys.argv[1]
    fields_file = sys.argv[2]
    output_path = sys.argv[3]
    signature_path = sys.argv[4] if len(sys.argv) > 4 else None
    form_type = sys.argv[5] if len(sys.argv) > 5 else "w9"

    try:
        with open(fields_file) as f:
            fields = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to read fields JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        reader = PdfReader(blank_path)
        writer = PdfWriter()
        writer.clone_reader_document_root(reader)

        # 1. Fill XFA
        fill_xfa(writer, fields)

        # 2. Add Signature
        if signature_path:
            # Clean path and check if it's a valid non-placeholder string
            clean_sig = signature_path.strip().strip('"').strip("'")
            if clean_sig.lower() not in ['', 'none', 'undefined', 'null']:
                add_signature(writer, clean_sig, form_type)
            else:
                print("DEBUG fill_pdf: Skipping signature (placeholder/empty)")

        with open(output_path, 'wb') as f:
            writer.write(f)
        
        print(f"OK: {output_path}")
    except Exception as e:
        print(f"ERROR: PDF processing failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
