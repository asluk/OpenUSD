"""Pixel-faithful PDF from inspected renders of the finalized editable PowerPoint."""

from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

root = Path(__file__).resolve().parents[1]
target = root / "delivery/output/Geospatial-USD-proposal-assessment.pdf"
pages = [root / f"delivery/deck-build/final-render/slide-{i}.png" for i in range(1, 13)]
assert all(p.is_file() for p in pages)
c = Canvas(str(target), pagesize=(960, 540))
c.setTitle("Geospatial USD: proposal quality and working evidence")
c.setAuthor("Aaron Luk / fresh build-loop assessment")
for page in pages:
    c.drawImage(ImageReader(str(page)), 0, 0, width=960, height=540)
    c.showPage()
c.save()
assert len(PdfReader(target).pages) == 12
print(target)
