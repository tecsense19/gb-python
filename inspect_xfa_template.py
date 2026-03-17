from pypdf import PdfReader
import sys

def dump_xfa_template(pdf_path):
    reader = PdfReader(pdf_path)
    xfa = reader.root_object["/AcroForm"]["/XFA"]
    
    template_xml = ""
    for i in range(0, len(xfa), 2):
        if xfa[i] == 'template':
            template_obj = xfa[i + 1].get_object()
            template_xml = template_obj.get_data().decode('utf-8', errors='ignore')
            break
            
    if template_xml:
        # Search for c1_1 in the template
        import re
        matches = re.findall(r'<field\b[^>]*?name="c1_1".*?</field>', template_xml, re.DOTALL)
        for i, m in enumerate(matches):
            print(f"--- c1_1 Match {i} ---")
            print(m)
            # Find bind info
            bind = re.search(r'<bind\b[^>]*?ref="(.*?)"', m)
            if bind:
                print(f"  Bind Ref: {bind.group(1)}")
    else:
        print("No XFA template found")

if __name__ == "__main__":
    dump_xfa_template(sys.argv[1])
