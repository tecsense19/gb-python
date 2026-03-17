from pypdf import PdfReader
import sys

def inspect_checkbox(pdf_path, field_name):
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if field_name in fields:
        field = fields[field_name]
        print(f"Details for {field_name}:")
        print(f"  Type: {field.get('/FT')}")
        print(f"  Export Value (Opt): {field.get('/Opt')}")
        print(f"  Toggle Value (V): {field.get('/V')}")
        print(f"  Appearance (AP): {field.get('/AP')}")
        # Look at the widget annotation
        for page in reader.pages:
            if "/Annots" in page:
                for annot in page["/Annots"]:
                    obj = annot.get_object()
                    if obj.get("/T") == field_name:
                        print(f"  Widget value: {obj.get('/V')}")
                        print(f"  Widget type: {obj.get('/FT')}")
                        print(f"  Widget appearance: {obj.get('/AS')}")
    else:
        print(f"Field {field_name} not found")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} file.pdf field_name")
    else:
        inspect_checkbox(sys.argv[1], sys.argv[2])
