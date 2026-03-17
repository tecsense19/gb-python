import json
from pypdf import PdfReader

def check_states():
    try:
        reader = PdfReader("W8forEntities.pdf")
        fields = reader.get_fields()
        res = {}
        for name, field in fields.items():
            if field.field_type == '/Btn':
                # The normal dictionary of a button might have /AP (Appearance) with /N (Normal)
                # which lists the states (e.g. /Off, /1, etc.)
                try:
                    ap = field.get('/AP', {})
                    n = ap.get('/N', {})
                    states = list(n.keys()) if hasattr(n, 'keys') else []
                    res[name] = states
                except Exception:
                    res[name] = "error"
        
        with open('button_states.json', 'w') as f:
            json.dump(res, f, indent=2)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_states()
