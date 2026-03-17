from pypdf import PdfReader
import sys

def inspect_all_checkboxes(pdf_path):
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    for i in range(7):
        field_name = f"topmostSubform[0].Page1[0].FederalClassification[0].c1_1[{i}]"
        if field_name in fields:
            field = fields[field_name]
            print(f"--- {field_name} ---")
            print(f"  Field Type (/FT): {field.get('/FT')}")
            print(f"  Export Value (/V): {field.get('/V')}")
            print(f"  Export Value (/DV): {field.get('/DV')}")
            # Check for /AP (Appearance) to see state names
            if "/AP" in field:
                ap = field["/AP"]
                if "/N" in ap:
                    states = ap["/N"].keys()
                    print(f"  Appearance States: {list(states)}")
        else:
            print(f"Field {field_name} not found")

if __name__ == "__main__":
    inspect_all_checkboxes(sys.argv[1])
