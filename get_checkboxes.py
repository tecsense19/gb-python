import json
from pypdf import PdfReader

def get_checkboxes():
    try:
        reader = PdfReader("W8forEntities.pdf")
        fields = reader.get_fields()
        res = {}
        for name, field in fields.items():
            if field.field_type == '/Btn':
                alt_name = field.mapping_name or ""
                res[name] = alt_name
        
        with open('checkboxes.json', 'w') as f:
            json.dump(res, f, indent=2)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_checkboxes()
