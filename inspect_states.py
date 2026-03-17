from pypdf import PdfReader
import sys

def inspect_widgets(pdf_path):
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    for i in range(7):
        name = f"topmostSubform[0].Page1[0].FederalClassification[0].c1_1[{i}]"
        if name in fields:
            field = fields[name]
            print(f"--- {name} ---")
            # The field dictionary might not have /AP directly if it's on the widget annotation
            # Let's find the annotation
            for page in reader.pages:
                if "/Annots" in page:
                    for annot in page["/Annots"]:
                        obj = annot.get_object()
                        if obj.get("/T") == name:
                            ap = obj.get("/AP")
                            if ap and "/N" in ap:
                                states = ap["/N"].keys()
                                print(f"  States: {list(states)}")
                            else:
                                print("  No /AP/N found")
        else:
            print(f"Field {name} not found")

if __name__ == "__main__":
    inspect_widgets(sys.argv[1])
