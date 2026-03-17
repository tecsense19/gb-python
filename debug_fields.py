from pypdf import PdfReader
import sys

def list_fields(pdf_path):
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if fields:
        for name in sorted(fields.keys()):
            # Filter for checkbox-like field names to reduce noise if there are many
            if "c1_1" in name or "FederalClassification" in name:
                print(name)
    else:
        print("No AcroForm fields found")

if __name__ == "__main__":
    list_fields(sys.argv[1])
