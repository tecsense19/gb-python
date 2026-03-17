import sys
from pypdf import PdfReader
if len(sys.argv) < 2:
    print(f"Usage: python {sys.argv[0]} file.pdf")
    sys.exit(1)

reader = PdfReader(sys.argv[1])
fields = reader.get_fields()
if fields:
    for name in fields.keys():
        print(name)
else:
    print("No AcroForm fields found")
