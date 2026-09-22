"""Prepare a public checkpoint and derive all summaries from its README."""
import hashlib
import html
import json
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import unquote

SOURCE_NAMES = {".gitattributes", ".gitignore", "run.py", "deliver.py", "build_deck.mjs", "derivation.json", "requirements.txt",
                "requirements-delivery.txt", "requirements-datasets.txt", "datasets.py", "dataset-catalog.json", "DATASETS.md",
                "pytest.ini", "Run-BuildLoop.ps1", "BUILD_LOOP.md", "package.json", "figures.py"}
PACKAGE = "extras/usd/examples/usdGeospatialBuild"
FORK = "asluk/OpenUSD"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_files(root):
    root = Path(root)
    return sorted(p for p in root.rglob("*") if p.is_file() and (
        (p.parent == root and p.name in SOURCE_NAMES) or
        (p.parent in (root / "geobuild", root / "tests") and p.suffix == ".py") or
        (p.parent == root / "native" and p.suffix in (".cpp", ".h", ".txt")) or
        (p.parent == root / "proposal" and p.suffix == ".md")))


def scan_text(text, label="text"):
    decoded = html.unescape(unquote(unquote(text)))
    rules = {
        "issue/pull-request URL": r"(?:https?://)?github\.com/[^\s/<>]+/[^\s/<>]+/(?:issues|pull)/\d+",
        "numbered issue/pull-request reference": r"(?<![\w/])(?:[\w.-]+(?:/[\w.-]+)?)?#\d+\b",
        "named issue/pull-request citation": r"\b(?:PR|issue|pull request)\s+\d+\b",
        "local machine path": r"[A-Za-z]:[\\/](?:Users|git)[\\/]",
        "private communication link": r"https?://[^\s]*(?:slack\.com|outlook\.office)[^\s]*",
    }
    for name, pattern in rules.items():
        if re.search(pattern, decoded, re.I):
            raise ValueError(f"Public delivery guard: {name} in {label}")


def scan_tree(root):
    root = Path(root)
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if "node_modules" in path.parts:
            continue
        if path.suffix.lower() in {".zip", ".usdz", ".usd", ".usda", ".usdc"}:
            raise ValueError(f"Unapproved dataset artifact in public delivery: {path.name}")
        if path.suffix.lower() in {".md", ".py", ".cpp", ".h", ".json", ".mjs", ".ps1", ".txt", ".ini", ".xml", ".html"}:
            scan_text(path.read_text(encoding="utf-8"), str(path.relative_to(root)))
        elif path.suffix.lower() == ".pptx":
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if name.endswith((".xml", ".rels")):
                        scan_text(archive.read(name).decode("utf-8"), f"{path.name}:{name}")
        elif path.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            scan_text("\n".join(page.extract_text() or "" for page in PdfReader(path).pages), path.name)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def public_source(source):
    return {k: source[k] for k in ("commit", "path", "review_state", "proposal_sha256",
                                 "allowed_text", "allowed_sha256", "requirements", "questions")}


def public_report(report):
    result = {k: report[k] for k in ("started_utc", "proposal_commit", "allowed_sha256", "derivation_current",
                                   "approval", "tests", "status", "source_files", "test_exit_code", "implementation", "stop_count")}
    result["source_files"] = {k.replace("\\", "/"): v for k, v in result["source_files"].items()}
    for key in ('complete_scope','native_build','demonstration_files'):
        if key in report:
            result[key]=report[key]
    result["environment"] = {k: report["environment"][k] for k in ("python", "platform", "packages")}
    dataset = report.get("dataset")
    result["dataset"] = ({k: dataset[k] for k in ("sha256", "origin", "redistribution", "role")} if dataset else None)
    if "dataset_inventory" in report:
        from geobuild.datasets import public_inventory
        result["dataset_inventory"] = public_inventory(report["dataset_inventory"])
        result["workflows"] = report["workflows"]
    if "runtime_contract" in report:
        result["runtime_contract"] = report["runtime_contract"]
    return result


def sections(readme):
    parts = re.split(r"^## (.+)\n", readme, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def slide_content(readme):
    if "<!-- narrative:v2 -->" in readme:
        from geobuild.narrative import slides
        return slides(readme)
    document = sections(readme)
    names = ["Checkpoint", "Runnable components", "Coordinate checks", "Sampled position path",
             "Partner baseline", "Open decisions", "Delivery for each run"]
    slides = [{"title": "usdGeospatial build loop", "lines": ["Functional requirements, runtime behavior and measured evidence", "Implementation checkpoint"]}]
    for title in names:
        lines = [re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", line[2:]).replace("**", "").replace("`", "")
                 for line in document[title].splitlines() if line.startswith("- ")]
        slides.append({"title": title, "lines": lines})
    match = re.search(r"Converted-first midpoint displacement: \*\*([0-9.]+) m\*\*", document["Sampled position path"])
    slides[4]["chart"] = {"categories": ["Native midpoint first", "Converted samples first"],
                           "values": [0, float(match[1])], "unit": "metres"}
    return {"readme_sha256": hashlib.sha256(readme.encode()).hexdigest(), "slides": slides}


def pr_body(readme, branch):
    if "<!-- narrative:v2 -->" in readme:
        from geobuild.narrative import review_guide
        return review_guide(readme, branch)
    document = sections(readme)
    base = f"https://github.com/{FORK}/blob/{branch}/{PACKAGE}"
    body = "\n\n".join([
        "A geospatial implementation needs an explicit runtime contract derived from functional requirements. This draft delivers the first runnable components and the evidence/decisions that determine the next increment.",
        document["Checkpoint"],
        "### What runs", document["Runnable components"],
        "### Review", f"Start with the [README]({base}/README.md). It is the source for this review guide and the [slide deck]({base}/docs/checkpoint.pdf).",
        f"The [runtime contract]({base}/docs/RUNTIME.md), [fixture matrix]({base}/docs/FIXTURES.md) and [build stops]({base}/docs/STOPS.md) connect the implementation to the requirements.",
        "### Validation", document["Coordinate checks"],
        "The README states the test scope, optional attachment checks, remaining decisions and reproduction commands. This checkpoint does not establish complete scene resolution or independent OpenUSD/OV agreement.",
    ]) + "\n"
    # GitHub PR bodies resolve relative links differently from repository files.
    body = re.sub(r"(\[[^]]+\]\()((?!https?://)[^)]+)(\))",
                  lambda m: m[1] + base + "/" + m[2] + m[3], body)
    scan_text(body, "PR body")
    return body


def metric(report, name, key):
    for test in report["tests"]:
        if test["name"] == name and test["status"] == "passed":
            value = test["properties"].get(key)
            return float(value) if value is not None else None
    return None


def make_readme(source, report, checkpoint_id):
    counts = {s: sum(t["status"] == s for t in report["tests"]) for s in ("passed", "failed", "skipped")}
    nreq, nq, stops = len(source["requirements"]), len(source["questions"]), report["stop_count"]
    residual = metric(report, "test_engine_analytic_global_points_and_provenance", "max_residual_m")
    magnitude = metric(report, "test_engine_analytic_global_points_and_provenance", "max_coordinate_magnitude_m")
    chord = metric(report, "test_native_sample_midpoint_before_conversion", "wrong_order_chord_depth_m")
    if None in (residual, magnitude, chord):
        raise ValueError("Required numerical evidence is missing.")
    partner = []
    if report.get("dataset"):
        origin = metric(report, "test_aeco_partner_stated_origin_and_conformance", "origin_residual_m")
        height = metric(report, "test_aeco_partner_stated_origin_and_conformance", "height_m")
        calibration = metric(report, "test_aeco_wkt_library_and_calibration_origin", "calibration_origin_residual_m")
        if None in (origin, height, calibration):
            raise ValueError("Attachment supplied but its evidence is missing.")
        partner = [f"- Tower-origin residual: **{origin:.6f} m** against the partner's stated coordinates.",
                   f"- Tower height: **{height:.6f} m** against the stated approximately 300 m.",
                   f"- Calibrated grid-origin residual: **{calibration * 1000:.6f} mm**."]
    else:
        partner = ["- The optional partner attachment was not supplied for this run."]
    partner += ["- These checks reproduce the existing stock-USD example. They do not validate a new scene resolver.",
                "- The attachment remains local because redistribution has not been established. Public reruns skip its two checks."]
    return f"""# usdGeospatial build loop

A reproducible experiment that derives runtime behavior from geospatial functional
requirements, implements bounded parts, tests them, and delivers the evidence for review.

## Checkpoint

- **{counts['passed']} tests passed, {counts['failed']} failed, {counts['skipped']} skipped** in this delivered run.
- **{nreq} functional requirements**, **{nq} numbered open questions** and **{stops} grouped build stops** are tracked.
- The requirements and runtime derivation remain drafts. Complete scene resolution and independent OpenUSD/OV agreement remain unimplemented.

Run record: [{checkpoint_id}](runs/{checkpoint_id}/report.json). Source input:
[bundled functional requirements](inputs/requirements.md), revision `{source['commit']}`.
Implementation revision: `{report['implementation']['revision']}`.
The [runtime derivation](docs/RUNTIME.md), [fixture matrix](docs/FIXTURES.md), [workflow evidence](docs/WORKFLOWS.md) and
[build stops](docs/STOPS.md) explain the scope of every result.

## Runnable components

- A read-only binding inspector reads composed USD relationships, nested overrides and forwarded targets.
- A PROJ adapter converts explicit WGS 84 geographic-3D and geocentric coordinates, with operation provenance and whole-batch failures.
- Input-change checks invalidate stale derivations before old tests can count as current evidence.
- Anchor decoding, placement matrices, scene-target selection, general datum/grid/epoch operations and OV integration remain pending.

## Coordinate checks

- Maximum measured Cartesian residual: **{residual:.9f} m** at a coordinate magnitude of **{magnitude:.3f} m**.
- Expected coordinates come from WGS 84 ellipsoid equations calculated separately from PROJ.
- The analytic check uses a **0.000001 m** numerical tolerance. This is a component-test tolerance.
- PROJ reports this operation's accuracy as **unknown**. A measured residual does not replace the engine's accuracy estimate.

## Sampled position path

- Converting the native midpoint first places the example point on the ellipsoid.
- Converted-first midpoint displacement: **{chord:.3f} m** below that point.
- This exercises requirement 20, Positions between recorded moments, using its equatorial example.
- Whether USD may record geographic positions, and which carrier holds them, remains open.

## Partner baseline

{chr(10).join(partner)}

## Open decisions

- S01: position carrier, geographic recording and the position/offset boundary.
- S02: preserving an asset's native CRS while placing it in a project.
- S03: scene units/up axis, the placement basis and its distance/extent bound.
- S04: consumer target selection and geographic scene output.
- S05: dependency declaration, explicit export and re-resolution.
- S06: practitioner controls, operation resources, a second engine and OV evidence.
- S07: complete rules for hierarchical binding relationships.

Each [stop](docs/STOPS.md) records the affected requirements, what is missing,
what an implementation would otherwise invent, and proposed feedback.

## Delivery for each run

- A successful test invocation produces an immutable checkpoint with the input revision, source hashes, environment, results and remaining decisions.
- Run evidence updates the README. The PR body and slide content are then derived from the README.
- A publication check rejects issue/PR citations, private paths and private communication links before a push or PR update.
- One standing draft PR receives each reviewed checkpoint. Earlier run records remain in the branch history.

[Slides (PDF)](docs/checkpoint.pdf) · [Editable slides](docs/checkpoint.pptx) ·
[Generated PR text](docs/PR_BODY.md) · [Run procedure](BUILD_LOOP.md).

## Reproduce

From this directory, use Python 3.12 with the pinned dependencies:

```sh
python -m pip install -r requirements.txt
python run.py --output /absolute/path/outside-checkout/run-001
```

The bundled input makes a public rerun independent of a proposal checkout.
Without the optional AECO attachment, two tests skip. Exit 2 means the cycle
completed with design/evidence gaps. Exit 1 means an execution or test failure.

To use a newer committed proposal, pass `--proposal-repo /path/to/checkout`.
To include the existing partner fixture locally, pass `--aeco-zip /path/to/attachment.zip`.
To prepare delivery after the tests, append `--deliver --checkpoint-id <new-id>`.
Slide export and publication are explicit phases described in [BUILD_LOOP.md](BUILD_LOOP.md).
"""


def prepare(run_dir, root, checkpoint_id=None, branch="aluk/geospatial-build-loop"):
    run_dir, root = Path(run_dir).resolve(), Path(root).resolve()
    scan_tree(root)
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    source = json.loads((run_dir / "source.json").read_text(encoding="utf-8"))
    if report["status"] != "COMPLETE_WITH_OPEN_DESIGN_QUESTIONS" or not report["derivation_current"] or report.get("test_exit_code") != 0:
        raise ValueError("Delivery requires a current derivation and a successful test invocation.")
    if not report.get('complete_scope') or not report["tests"] or any(t["status"] != "passed" for t in report["tests"]):
        raise ValueError("Delivery requires the complete scope and no skipped workflows or checks.")
    expected = {k.replace("\\", "/"): v for k, v in report["source_files"].items()}
    actual = {p.relative_to(root).as_posix(): sha(p) for p in source_files(root)}
    if expected != actual:
        raise ValueError("Build source changed since the run. Rerun before delivery.")
    if "runtime_contract" in report:
        for name, relative in (("RUNTIME-BEHAVIOR.md", "proposal/runtime-behavior.md"),
                               ("RUNTIME-OPEN-DECISIONS.md", "proposal/runtime-open-decisions.md"),
                               ("RUNTIME-EXPERIMENTS.md", "proposal/runtime-experiments.md")):
            if sha(run_dir / name) != actual[relative]:
                raise ValueError("Runtime prose changed since the run.")
    if "dataset_inventory" in report:
        from geobuild.datasets import workflow_evidence, render_workflows
        catalog_file = run_dir / "dataset-catalog.json"
        if sha(catalog_file) != report["dataset_inventory"]["catalog_sha256"]:
            raise ValueError("Workflow catalog changed since the run.")
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
        if report["workflows"] != workflow_evidence(catalog, report):
            raise ValueError("Workflow evidence does not match executed checks.")
        if (run_dir / "WORKFLOWS.md").read_text(encoding="utf-8") != render_workflows(source, report):
            raise ValueError("Workflow explanation changed since the run.")
    checkpoint_id = checkpoint_id or re.sub(r"[^0-9]", "", report["started_utc"])[:14]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", checkpoint_id):
        raise ValueError("Invalid checkpoint identifier.")
    destination = root / "runs" / checkpoint_id
    if destination.exists():
        raise ValueError("Checkpoint already exists; run records are immutable.")
    clean_source, clean_report = public_source(source), public_report(report)
    authored = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").exists() else ""
    if "<!-- narrative:v2 -->" in authored:
        from geobuild.narrative import refresh, verify_figures
        verify_figures(root, report)
        readme = refresh(authored, clean_source, clean_report, checkpoint_id)
    else:
        readme = make_readme(clean_source, clean_report, checkpoint_id)
    body = pr_body(readme, branch)
    deck = slide_content(readme)
    for label, value in (("source", clean_source), ("report", clean_report), ("README", readme), ("slides", deck)):
        scan_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False), label)
    inputs, docs = root / "inputs", root / "docs"
    for folder in (inputs, docs, destination):
        folder.mkdir(parents=True, exist_ok=True)
    write_json(inputs / "requirements.json", clean_source)
    (inputs / "requirements.md").write_text(source["allowed_text"], encoding="utf-8", newline="\n")
    write_json(destination / "report.json", clean_report)
    history_readme = readme.replace(f"(runs/{checkpoint_id}/report.json)", "(report.json)")
    history_readme = history_readme.replace("(inputs/requirements.md)", "(requirements.md)")
    for name in ("RUNTIME.md", "FIXTURES.md", "WORKFLOWS.md", "STOPS.md", "checkpoint.pdf", "checkpoint.pptx", "PR_BODY.md"):
        history_readme = history_readme.replace(f"(docs/{name})", f"({name})")
    history_readme = history_readme.replace("(BUILD_LOOP.md)", "(../../BUILD_LOOP.md)")
    history_readme = history_readme.replace("(docs/figures/", "(figures/")
    history_readme = history_readme.replace("(proposal/runtime-behavior.md)", "(RUNTIME-BEHAVIOR.md)")
    history_readme = history_readme.replace("(proposal/runtime-open-decisions.md)", "(RUNTIME-OPEN-DECISIONS.md)")
    history_readme = history_readme.replace("(proposal/runtime-experiments.md)", "(RUNTIME-EXPERIMENTS.md)")
    history_readme = history_readme.replace("(DATASETS.md)", "(../../DATASETS.md)")
    (destination / "README.md").write_text(history_readme, encoding="utf-8", newline="\n")
    (root / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    (docs / "PR_BODY.md").write_text(body, encoding="utf-8", newline="\n")
    (destination / "PR_BODY.md").write_text(body, encoding="utf-8", newline="\n")
    write_json(docs / "slides.json", deck)
    if (run_dir / "dataset-catalog.json").exists():
        catalog_text = (run_dir / "dataset-catalog.json").read_text(encoding="utf-8")
        scan_text(catalog_text, "dataset catalog")
        (destination / "dataset-catalog.json").write_text(catalog_text, encoding="utf-8", newline="\n")
    for name in ("RUNTIME.md", "FIXTURES.md", "WORKFLOWS.md", "STOPS.md", "AGENT-BRIEF.md"):
        text = (run_dir / name).read_text(encoding="utf-8")
        scan_text(text, name)
        (docs / name).write_text(text, encoding="utf-8", newline="\n")
        (destination / name).write_text(text, encoding="utf-8", newline="\n")
    if "runtime_contract" in report:
        if sha(run_dir / "RUNTIME-BEHAVIOR.md") != report["runtime_contract"]["sha256"]:
            raise ValueError("Runtime prose changed since the run.")
        for name in ("RUNTIME-BEHAVIOR.md", "RUNTIME-OPEN-DECISIONS.md", "RUNTIME-EXPERIMENTS.md"):
            shutil.copyfile(run_dir / name, docs / name)
            shutil.copyfile(run_dir / name, destination / name)
    if "<!-- narrative:v2 -->" in readme:
        shutil.copytree(docs / "figures", destination / "figures")
    (destination / "requirements.md").write_text(source["allowed_text"], encoding="utf-8", newline="\n")
    manifest = {"checkpoint": checkpoint_id, "proposal_commit": source["commit"],
                "implementation_revision": report["implementation"]["revision"],
                "requirements_sha256": source["allowed_sha256"], "readme_sha256": sha(root / "README.md"),
                "report_sha256": sha(destination / "report.json"), "branch": branch,
                "test_status": report["status"], "record_kind": "prepared checkpoint; deck receipt and publish receipt record later phases"}
    write_json(docs / "delivery.json", manifest)
    scan_tree(root)
    return destination


def verify(root, require_slides=True):
    root = Path(root)
    manifest = json.loads((root / "docs" / "delivery.json").read_text(encoding="utf-8"))
    readme = (root / "README.md").read_text(encoding="utf-8")
    if sha(root / "README.md") != manifest["readme_sha256"]:
        raise ValueError("README changed after preparation; regenerate delivery.")
    if (root / "docs" / "PR_BODY.md").read_text(encoding="utf-8") != pr_body(readme, manifest["branch"]):
        raise ValueError("PR body drifted from the README.")
    if json.loads((root / "docs" / "slides.json").read_text(encoding="utf-8")) != slide_content(readme):
        raise ValueError("Slide content drifted from the README.")
    report_path = root / "runs" / manifest["checkpoint"] / "report.json"
    if sha(report_path) != manifest["report_sha256"]:
        raise ValueError("Checkpoint evidence changed after preparation.")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    actual = {p.relative_to(root).as_posix(): sha(p) for p in source_files(root)}
    if actual != report["source_files"]:
        raise ValueError("Source changed after preparation; rerun before publication.")
    if "runtime_contract" in report:
        for path in (root / report["runtime_contract"]["path"], root / "docs" / "RUNTIME-BEHAVIOR.md", report_path.parent / "RUNTIME-BEHAVIOR.md"):
            if sha(path) != report["runtime_contract"]["sha256"]:
                raise ValueError("Runtime prose differs from tested derivation.")
        for path in (root / "docs" / "RUNTIME-OPEN-DECISIONS.md", report_path.parent / "RUNTIME-OPEN-DECISIONS.md"):
            if sha(path) != report["source_files"]["proposal/runtime-open-decisions.md"]:
                raise ValueError("Open runtime decisions differ from the run.")
    if "runtime_contract" in report:
        for path in (root / "docs/RUNTIME-EXPERIMENTS.md", report_path.parent / "RUNTIME-EXPERIMENTS.md"):
            if sha(path) != report["source_files"]["proposal/runtime-experiments.md"]:
                raise ValueError("Candidate contract differs from the run.")
    if "<!-- narrative:v2 -->" in readme:
        from geobuild.narrative import verify_figures
        verify_figures(root, report)
        for path in (root / "docs" / "figures").iterdir():
            if path.is_file() and sha(path) != sha(report_path.parent / "figures" / path.name):
                raise ValueError("Archived figures differ from the delivered run.")
    if "dataset_inventory" in report:
        from geobuild.datasets import render_workflows
        catalog_file = report_path.parent / "dataset-catalog.json"
        if sha(catalog_file) != report["dataset_inventory"]["catalog_sha256"]:
            raise ValueError("Workflow catalog changed after preparation.")
        source = json.loads((root / "inputs" / "requirements.json").read_text(encoding="utf-8"))
        expected_workflows = render_workflows(source, report)
        for path in (root / "docs" / "WORKFLOWS.md", report_path.parent / "WORKFLOWS.md"):
            if path.read_text(encoding="utf-8") != expected_workflows:
                raise ValueError("Workflow explanation changed after preparation.")
    if require_slides:
        receipt = json.loads((root / "docs" / "deck-receipt.json").read_text(encoding="utf-8"))
        if receipt["readme_sha256"] != manifest["readme_sha256"]:
            raise ValueError("Slides belong to a different README.")
        for name in ("checkpoint.pptx", "checkpoint.pdf"):
            if sha(root / "docs" / name) != receipt["files"][name]:
                raise ValueError("Slide artifact does not match its receipt.")
    scan_tree(root)
    return manifest


def seal_slides(root, pptx, pdf):
    root = Path(root)
    manifest = verify(root, require_slides=False)
    with zipfile.ZipFile(pptx) as archive:
        notes = "\n".join(archive.read(n).decode("utf-8") for n in archive.namelist()
                          if n.startswith("ppt/notesSlides/notesSlide") and n.endswith(".xml"))
        if manifest["readme_sha256"] not in notes:
            raise ValueError("PPTX does not carry the current README provenance.")
        slide_count = sum(bool(re.fullmatch(r"ppt/slides/slide\d+\.xml", n)) for n in archive.namelist())
    from pypdf import PdfReader
    expected = len(slide_content((root / "README.md").read_text(encoding="utf-8"))["slides"])
    if slide_count != expected or len(PdfReader(pdf).pages) != expected:
        raise ValueError("PPTX/PDF slide count differs from the README-derived content.")
    for source, name in ((pptx, "checkpoint.pptx"), (pdf, "checkpoint.pdf")):
        shutil.copyfile(source, root / "docs" / name)
        archive = root / "runs" / manifest["checkpoint"] / name
        if archive.exists() and sha(archive) != sha(source):
            raise ValueError("Checkpoint slides already sealed; create a new checkpoint to revise them.")
        if not archive.exists():
            shutil.copyfile(source, archive)
    receipt = {"readme_sha256": manifest["readme_sha256"], "slides": expected,
               "files": {name: sha(root / "docs" / name) for name in ("checkpoint.pptx", "checkpoint.pdf")}}
    write_json(root / "docs" / "deck-receipt.json", receipt)
    verify(root)
    return receipt
