from pypdf import PdfReader
import sys

def dump_xfa(pdf_path):
    reader = PdfReader(pdf_path)
    xfa = reader.root_object["/AcroForm"]["/XFA"]
    
    datasets_obj = None
    for i in range(0, len(xfa), 2):
        if xfa[i] == 'datasets':
            datasets_obj = xfa[i + 1].get_object()
            break
            
    if datasets_obj:
        xml = datasets_obj.get_data().decode('utf-8')
        print(xml)
    else:
        print("No XFA datasets found")

if __name__ == "__main__":
    dump_xfa(sys.argv[1])
