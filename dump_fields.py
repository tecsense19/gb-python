import sys
from pypdf import PdfReader

def main():
    reader = PdfReader("W8forEntities.pdf")
    fields = reader.get_fields()
    if fields:
        for name in fields.keys():
            print(name)
    else:
        print("No fields found")

if __name__ == "__main__":
    main()
