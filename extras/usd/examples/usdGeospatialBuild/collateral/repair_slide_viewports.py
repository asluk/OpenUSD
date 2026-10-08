"""Repair only PowerPoint picture viewports; preserve every embedded image byte."""
from pathlib import Path
import hashlib
import sys
import zipfile
import xml.etree.ElementTree as ET

candidate = Path(sys.argv[1])
ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
with zipfile.ZipFile(candidate) as archive:
    parts = {item.filename: archive.read(item.filename) for item in archive.infolist()}
before = {key: hashlib.sha256(value).hexdigest() for key, value in parts.items() if key.startswith("ppt/media/")}
for number in (3, 4):
    key = f"ppt/slides/slide{number}.xml"
    root = ET.fromstring(parts[key])
    crops = root.findall(".//a:srcRect", ns)
    assert len(crops) == 1, (number, len(crops))
    # The informative source page is 1600 x 1560. Its photograph/annotations
    # occupy y=140..1040. Native crop values are in hundred-thousandths.
    crops[0].attrib.update(l="0", t="8974", r="0", b="33333")
    parts[key] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
temporary = candidate.with_name(candidate.stem + ".viewport-repair.pptx")
with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
    for key, value in parts.items():
        archive.writestr(key, value)
with zipfile.ZipFile(temporary) as archive:
    after = {key: hashlib.sha256(archive.read(key)).hexdigest() for key in before}
assert before == after, "Image bytes changed"
temporary.replace(candidate)
print("Repaired two native picture viewports; embedded image bytes unchanged")
