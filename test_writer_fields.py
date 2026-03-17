from pypdf import PdfReader, PdfWriter
reader = PdfReader("fw9_blank.pdf")
writer = PdfWriter()
writer.clone_reader_document_root(reader)
try:
    fields = writer.get_fields()
    print(f"Fields count in writer: {len(fields)}")
except Exception as e:
    print(f"Error getting fields from writer: {e}")
