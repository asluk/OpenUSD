"""Canonical proposed runtime prose, with implementation traceability separate."""
import hashlib
from pathlib import Path
import re


def load_contract(root, derivation):
    relative = derivation["runtime_document"]["path"]
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if root not in path.parents:
        raise ValueError("Runtime document must be inside the build package")
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## (.+)\n", text, flags=re.M)
    sections = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
    for entry in derivation["contracts"]:
        if entry["runtime_section"] not in sections:
            raise ValueError("Missing traced runtime-prose section")
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "text": text, "sections": sections, "approval": "proposed normative text; draft and incomplete"}
