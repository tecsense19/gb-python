#!/usr/bin/env python3
"""
fill_w9.py — Fills the IRS W-9 XFA PDF correctly.
Uses pypdf which rebuilds the xref table automatically when objects change.

Usage:
    python3 fill_w9.py <blank.pdf> <fields.json> <output.pdf>

Install:
    pip install pypdf
"""

import sys, json, re
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("ERROR: Run:  pip install pypdf", file=sys.stderr)
    sys.exit(1)


def fill_w9(blank_path: str, fields: dict, output_path: str) -> bool:
    reader = PdfReader(blank_path)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    # Get XFA datasets object via the writer's object graph
    acro = writer._root_object["/AcroForm"].get_object()
    xfa  = acro["/XFA"]

    datasets_obj = None
    for i in range(0, len(xfa), 2):
        if xfa[i] == 'datasets':
            datasets_obj = xfa[i + 1].get_object()
            break

    if datasets_obj is None:
        print("ERROR: XFA datasets stream not found", file=sys.stderr)
        return False

    # pypdf auto-decompresses get_data()
    xml = datasets_obj.get_data().decode('utf-8')

    # Inject field values
    for tag, value in fields.items():
        safe = (str(value)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))
        # Self-closing tag:  <f1_1/>  or  <f1_1\n/>
        xml = re.sub(r'<' + re.escape(tag) + r'\s*/>', f'<{tag}>{safe}</{tag}>', xml)
        # Tag with content:  <c1_1>0</c1_1>
        xml = re.sub(r'<' + re.escape(tag) + r'\s*>(.*?)</' + re.escape(tag) + r'\s*>',
                     f'<{tag}>{safe}</{tag}>', xml, flags=re.DOTALL)

    # Write back — uncompressed so pypdf re-encodes + rebuilds xref correctly
    datasets_obj._data = xml.encode('utf-8')
    if '/Filter' in datasets_obj:
        del datasets_obj['/Filter']
    if '/DecodeParms' in datasets_obj:
        del datasets_obj['/DecodeParms']

    with open(output_path, 'wb') as f:
        writer.write(f)

    return Path(output_path).stat().st_size > 0


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f"Usage: python3 {sys.argv[0]} blank.pdf fields.json output.pdf")
        sys.exit(1)

    blank, fields_file, output = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(fields_file) as f:
        fields = json.load(f)

    if fill_w9(blank, fields, output):
        print(f"OK: {output}")
        sys.exit(0)
    else:
        sys.exit(1)
