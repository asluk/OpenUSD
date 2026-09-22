"""Refresh bounded evidence in an authored README; derive review and slide text."""
import hashlib
import json
import re


def evidence_key(report):
    value = {k: report[k] for k in ("started_utc", "tests", "runtime_contract")}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def verify_figures(root, report):
    from geobuild.delivery import sha
    folder = root / "docs" / "figures"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["evidence_key"] != evidence_key(report):
        raise ValueError("Figures belong to a different run; regenerate them.")
    if set(manifest["files"]) != {"railway.png", "interpolation.png", "field.png"}:
        raise ValueError("Incomplete figure set")
    for name, expected in manifest["files"].items():
        if sha(folder / name) != expected:
            raise ValueError("Evidence figure changed after generation")


def refresh(readme, source, report, checkpoint_id):
    from geobuild.delivery import metric
    def value(test, key):
        answer = metric(report, test, key)
        if answer is None:
            raise ValueError(f"Narrative needs executed evidence: {test}/{key}; revise scope if unavailable")
        return answer
    features = value("test_workflow_geojson_source_to_usd_identity_and_anchors", "matched_feature_ids")
    lines = value("test_workflow_railway_source_inventory_and_anchor_reporting", "curve_prims")
    vertices = value("test_workflow_geojson_source_to_usd_identity_and_anchors", "matched_linestring_vertices_by_count")
    samples = value("test_workflow_field_coordinate_probe", "samples")
    chord = value("test_native_sample_midpoint_before_conversion", "wrong_order_chord_depth_m")
    residual = value("test_engine_analytic_global_points_and_provenance", "max_residual_m")
    counts = {s: sum(t["status"] == s for t in report["tests"]) for s in ("passed", "failed", "skipped")}
    blocks = {
        "railway": f"- {features:,.0f} source features match USD object identities and first-coordinate anchors.\n- {lines:,.0f} railway curves retain {vertices:,.0f} vertices by count; interior placement is still unchecked.",
        "interpolation": f"- Interpolating converted endpoints puts the equatorial midpoint {chord:,.3f} m inside the ellipsoid.",
        "field": f"- {samples:,.0f} scalar samples on a 37 by 72 grid exercise coordinate reporting; a three-sample overlay is removable.",
        "run": f"**{counts['passed']} passed, {counts['failed']} failed, {counts['skipped']} skipped.** These are component and build-integrity checks, not full-workflow conformance.\n\nRun record: [{checkpoint_id}](runs/{checkpoint_id}/report.json). Requirements revision: `{source['commit']}`.\nRuntime prose SHA-256: `{report['runtime_contract']['sha256']}`.\nImplementation base: `{report['implementation']['revision']}`; local changes: **{str(report['implementation']['source_dirty']).lower()}**. Exact tested files are hashed in the run record.\n\nThe original analytic coordinate probe measured a maximum Cartesian residual of **{residual:.9f} m**. Its 0.000001 m numerical tolerance is not a scene-placement accuracy budget; PROJ's operation accuracy estimate remains unknown.",
    }
    for name, text in blocks.items():
        pattern = rf"(<!-- evidence:{name} -->).*?(<!-- /evidence:{name} -->)"
        readme, count = re.subn(pattern, lambda m: m[1] + "\n" + text + "\n" + m[2], readme, flags=re.S)
        if count != 1:
            raise ValueError("Missing or duplicate README evidence block: " + name)
    return readme


def slides(readme):
    from geobuild.delivery import sections
    result = []
    for title, body in sections(readme).items():
        if "<!-- slide -->" not in body:
            continue
        lines = [re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", s[2:]).replace("**", "").replace("`", "")
                 for s in body.splitlines() if s.startswith("- ")]
        if not 2 <= len(lines) <= 4:
            raise ValueError("A slide section needs two to four selected claims: " + title)
        item = {"title": title, "lines": lines}
        picture = re.search(r"!\[([^]]+)\]\((docs/figures/[^)]+)\)", body)
        if picture:
            item.update(image=picture[2], caption=picture[1])
        result.append(item)
    if not result:
        raise ValueError("No README slide sections")
    return {"readme_sha256": hashlib.sha256(readme.encode()).hexdigest(), "slides": result}


def review_guide(readme, branch):
    from geobuild.delivery import FORK, PACKAGE, scan_text, sections
    doc = sections(readme)
    selected = ["Geospatial scenes with shared placement", "Railway source and scene identity", "Two runtime targets", "Next complete demonstration", "Review requests"]
    body = "# Runtime behavior and workflow evidence\n\n" + "\n\n".join(
        "### " + title + "\n\n" + "\n".join(line for line in doc[title].splitlines() if line.startswith("- "))
        for title in selected)
    evidence = re.sub(r"<!--.*?-->", "", doc["Run evidence"], flags=re.S).strip()
    body += "\n\n### Run evidence\n\n" + evidence.split("\n\n", 1)[0]
    body += "\n\nStart with the [README](README.md), [proposed runtime behavior](proposal/runtime-behavior.md), and [slides](docs/checkpoint.pdf).\n"
    base = f"https://github.com/{FORK}/blob/{branch}/{PACKAGE}"
    body = re.sub(r"(\[[^]]+\]\()((?!https?://)[^)]+)(\))", lambda m: m[1] + base + "/" + m[2] + m[3], body)
    scan_text(body, "PR review guide")
    return body
