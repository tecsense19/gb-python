from pypdf import PdfReader
import sys

reader = PdfReader("test_w9_new.pdf")
acro = reader.root_object["/AcroForm"].get_object()
xfa = acro["/XFA"]

datasets_obj = None
for i in range(0, len(xfa), 2):
    if xfa[i] == 'datasets':
        datasets_obj = xfa[i + 1].get_object()
        break

if datasets_obj:
    xml = datasets_obj.get_data().decode('utf-8', errors='ignore')
    print(xml[:2000])
else:
    print("No datasets found")
