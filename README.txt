W-9 PDF Filler — Final Working Version
========================================

WHY PYTHON IS REQUIRED:
  The IRS W-9 uses XFA (XML Forms Architecture). After modifying the
  internal XML stream, the PDF cross-reference (xref) table must be
  rebuilt — otherwise Adobe Reader shows blank fields.
  pypdf does this automatically. Pure PHP cannot without a full PDF writer.

FILES:
  w9_handler.php         ← PHP form (browser UI + calls Python)
  fill_w9.py             ← Python PDF engine (xref-safe XFA injection)
  fw9_blank.pdf          ← Original IRS W-9 template (DO NOT replace)
  sample_filled_w9.pdf   ← Pre-filled sample to verify it works
  filled/                ← Temp output dir (must be writable)

SETUP:
  1. Install Python dependency (once):
       pip install pypdf

  2. Upload all files to same server folder

  3. Set permissions:
       chmod 755 filled/
       chmod 755 fill_w9.py

  4. Open w9_handler.php in browser

VERIFY PYTHON PATH:
  If PDF generation fails, check which python command your server uses:
       which python3   →  use python3
       which python    →  use python
  The PHP file tries both automatically.

REQUIREMENTS:
  PHP 7.4+  |  Python 3.7+  |  pypdf library
