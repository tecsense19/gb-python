from pypdf import PdfReader
import sys

def dump_xfa_template_raw(pdf_path):
    reader = PdfReader(pdf_path)
    try:
        xfa = reader.root_object["/AcroForm"]["/XFA"]
    except KeyError:
        print("AcroForm/XFA not found")
        return
    
    for i in range(0, len(xfa), 2):
        if xfa[i] == 'template':
            template_obj = xfa[i + 1].get_object()
            data = template_obj.get_data()
            print(f"Template Data Length: {len(data)}")
            # Try to save it to a file for easier inspection
            with open("template_debug.xml", "wb") as f:
                f.write(data)
            print("Template saved to template_debug.xml")
            
            # Print first 500 chars
            print("--- First 500 chars ---")
            print(data[:500].decode('utf-8', errors='ignore'))
            break

if __name__ == "__main__":
    dump_xfa_template_raw(sys.argv[1])
