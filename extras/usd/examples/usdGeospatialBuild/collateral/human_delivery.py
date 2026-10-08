"""Informative proposal assessment -> README -> the same words in review/slides.

This module adds no normative authority. Every case binds to the executed
proposal, receipt and later audit. A changed authority/evidence requires a new
assessment rather than silently reusing an old explanation.
"""
from pathlib import Path
import hashlib
import json
import re


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def markdown_table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(str(v).replace("\n", " ") for v in row) + " |" for row in rows),
    ])


ISSUE_TEXT = {
    "A1": ["Surface lighting directions", "A private sampling shortcut has no justified error bound. One projected case differs by about 1.24 degrees."],
    "A2": ["Repeated models", "A referenced model outside the bound subtree fails instead of receiving the instancer's placement."],
    "A3": ["Baked geometry", "Two source triangles become three output triangles. The check misses the extra geometry."],
    "A4": ["Measurement locations", "A different array dimension order pairs four of six values with the wrong locations. Both readers share this decoder."],
    "A5": ["Other scene information", "The bake removes an unrelated MotionAPI schema application, changing other scene meaning."],
    "A6": ["Error reporting", "Reports omit required per-component errors and separate angular errors."],
    "A7": ["Invalid input detection", "An invalid placement attribute on an inherited-only child is silently ignored."],
}


def prepare(root, base, assessment_path, audit_path):
    root = Path(root)
    assessment = json.loads(Path(assessment_path).read_text(encoding="utf-8"))
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    assert assessment["proposal_sha256"] == base["proposal_sha256"], "Reassess the changed proposal"
    assert assessment["execution_receipt_sha256"] == base["immutable_receipt_sha256"], "Reassess the changed execution"
    assert assessment["audit_source_sha256"] == audit["source_audit_sha256"], "Reassess the changed audit"
    assert audit["execution_receipt_sha256"] == base["immutable_receipt_sha256"], "Audit belongs to a different execution"
    assert audit["proposal_sha256"] == base["proposal_sha256"]
    authority = (root / "proposal/proposal-source.txt").read_text(encoding="utf-8")
    assert sha(root / "proposal/proposal-source.txt") == base["proposal_sha256"]
    quality = json.loads((root / "proposal-quality.json").read_text(encoding="utf-8"))
    requirements = {r["id"]: r for r in quality["requirements"]}
    confirmed = [f for f in audit["findings"] if f["id"].startswith("A")]
    assert {f["id"] for f in confirmed} == set(ISSUE_TEXT), "Current issue explanations must be reassessed"
    context = {
        "child_difference": base["comparison"]["difference_metres"],
        "max_difference": base["max_cpp_error_metres"],
        "chord_difference": base["chord_error_metres"],
        "global_samples": base["dataset_counts"]["global_samples"],
        "railway_vertices": base["dataset_counts"]["railway_vertices"],
        "railway_parts": base["dataset_counts"]["railway_parts"],
    }
    cases = []
    for original in assessment["cases"]:
        case = dict(original)
        for field in ["question", "rule", "expected", "observed", "implication", "boundary"]:
            assert case.get(field), (case["id"], "Missing assessment field", field)
            case[field] = case[field].format_map(context)
        lines = authority.splitlines()
        indices = [i + 1 for i, line in enumerate(lines) if line == case["clause_heading"]]
        assert len(indices) == 1, (case["id"], case["clause_heading"], "Missing/ambiguous proposal authority")
        case["clause_line"] = indices[0]
        case["requirements"] = [{"id": n, "title": requirements[n]["title"], "line": requirements[n]["source_line"]} for n in case["requirement_ids"]]
        if case.get("image"):
            assert case["image"]["role"] in {"informative illustration", "recorded native render", "plot of recorded synthetic data", "plot of recorded resolved geometry"}
            assert (root / "delivery" / case["image"]["path"]).is_file(), case["image"]["path"]
        cases.append(case)
    return assessment, cases, audit, confirmed


def publish(root, base, assessment_path, audit_path):
    root = Path(root)
    assessment, cases, audit, confirmed = prepare(root, base, assessment_path, audit_path)
    by_id = {c["id"]: c for c in cases}
    issues = [[ISSUE_TEXT[f["id"]][0], f["result_summary"]] for f in confirmed]
    unresolved = [f for f in confirmed if f["status"] == "confirmed unresolved"]
    status_rows = [
        ["Proposal definitions", "A focused requirements baseline is separate from the full candidate used for execution. Supported meaning and pending conventions are distinguished."],
        ["Newly confirmed model gap", "No additional undefined model rule was confirmed in reviewed paths. This is a scoped assessment, not an exhaustive completeness proof."],
        ["Implementation evidence", f"The selected cases work. {len(confirmed)-len(unresolved)} prior defects pass fresh counterexamples; {len(unresolved)} remains unresolved."],
        ["Deferred capabilities", "Coordinate epochs and scene-authored transformation resources remain on the roadmap. Initial choices must preserve a path to adding them."],
    ]
    inputs = [
        ["Model geometry", "Shape and local distances, with declared model units and up direction. In USD: points, metersPerUnit and upAxis."],
        ["Coordinate reference", "A CRS binding refers to WKT, the standard text description of the location's axes, units and height meaning."],
        ["Geographic origin", "crs:position locates the model origin. The illustrative example uses longitude 2.2945 degrees, latitude 48.8584 degrees and ellipsoidal height 80 m."],
        ["Physical orientation", "crs:orientation stores heading, pitch and roll in degrees: which way the model faces and tilts at its origin."],
    ]
    placement_choices = [
        ["Physical orientation", "Preferred HPR tuple in degrees, with explicit pose interpolation. Authored inputs only; adoption pending."],
        ["The object with its own georeference", "Project adjustment meaning is supported. The detailed fixed working-frame convention remains a candidate."],
        ["Child objects", "Model-local meaning is supported. The follow-up specifies chart/reset details and tests that offsets retain their interpretation."],
        ["Independently georeferenced repeated models", "Keep a prototype's own geographic placement and apply each instance effect once."],
        ["Geographic queries and scene geometry", "Return longitude/latitude/height for geographic queries. Cartesian geometry and bounds use the datum's Earth-centred frame."],
    ]
    data_choices = [
        ["Native data association", "Name the asset, format, field and coordinate domain. Preserve the association between values, locations and observation times."],
        ["WKT string normalization", "A prescribed text form supports token comparison. Different normalized texts can still describe equivalent CRSs."],
        ["Semantic CRS comparison", "Specify equivalence criteria and the comparison domain, accounting for relevant axes, units and metadata."],
        ["Dependency declaration using Profiles", "Declare the composed scene's need for geospatial interpretation, including unloaded content. Writers and assemblers maintain the declaration."],
        ["Baked output context", "Record a Cartesian CRS and ordinary double-precision origin. Preserve precision and space/time coverage."],
    ]
    evidence_rows = [
        ["Python and C++ readers", f"{base['coordinate_count']:,} coordinate results per reader. Maximum measured difference {base['max_cpp_error_metres']:.3g} m. They share PROJ and native dataset decoding."],
        ["Omniverse stage geometry integration", f"Reuses Python placement. Recorded readback covers {base['ov']['geometry_vertices']:,} geometry vertices and {base['ov']['edit_checks']} edit, failure and recovery checks, across {base['ov']['jobs']} jobs."],
        ["Hydra / Storm", "Two selected ordinary USD bakes reach native rendering. This consumer path uses the C++ placement results."],
        ["Recorded tests", f"{base['tests']['regressions_passed']} regressions and {base['tests']['distinguishing_controls_passed']} distinguishing controls passed. Fresh independent diagnostics verify six repairs and retain the unresolved normal case."],
        ["Source preservation", "Original inputs and all frozen execution files remained unchanged during this run. The immutable receipt identifies the exact executed content."],
        ["Bake readbacks", f"{base['export_count']} selected exports were checked. The fresh nested-geometry counterexample verifies the complete inventory, including unexpected extras."],
    ]

    def case_markdown(case):
        source = f"[{case['clause_heading'].lstrip('# ')}](proposal/proposal-source.txt#L{case['clause_line']})"
        refs = ", ".join(f"[{r['id']}](proposal/proposal-source.txt#L{r['line']})" for r in case["requirements"])
        result = f"### {case['title']}\n\n**Question.** {case['question']}\n\n{case['rule']}\n\n"
        if case.get("image"):
            image = case["image"]
            result += f"![{image['alt']}](delivery/{image['path']})\n\n*{image['role'].capitalize()}. {case['boundary']}*\n\n"
        result += f"**Expected behavior.** {case['expected']}\n\n**Observed result.** {case['observed']}\n\n**What this says about the proposal.** {case['implication']}\n\n"
        if not case.get("image"):
            result += f"**Limit.** {case['boundary']}\n\n"
        result += f"Proposal basis: {source}. Functional requirements {refs}.\n\n"
        return result

    text = f"# {assessment['title']}\n\n{assessment['opening']}\n\n{assessment['assessment']}\n\n"
    text += "[Slides](delivery/geospatial-build.pptx) · [PDF](delivery/geospatial-build.pdf) · [Proposal snapshot](proposal/proposal-source.txt) · [Build loop](BUILD_LOOP.md)\n\n"
    text += "## Assessment of the proposal\n\n" + markdown_table(["Review dimension", "Current assessment"], status_rows) + "\n\n"
    text += assessment["summary"] + "\n\n"
    if assessment.get("comparison"):
        text += "## Changes since the previous run\n\n" + assessment["comparison"]["explanation"] + "\n\n"
        text += markdown_table(["Compared aspect", "Finding"], assessment["comparison"]["rows"]) + "\n\n"
        text += "[Full comparison](delivery/run-comparison.json)\n\n"
    text += "## Source inputs and computed placement\n\n" + case_markdown(by_id["inputs"]) + markdown_table(["Source information", "Plain meaning"], inputs) + "\n\n"
    text += "A reader computes coordinate-query results and scene placement from those inputs. Projection scale, convergence and other computed results do not become source geospatial properties. An ordinary USD scale operation records an author's intentional adjustment.\n\n"
    text += "## Demonstrations and their meaning\n\n"
    for key in ["coordinates", "adjustments", "readers", "bake", "measurements"]:
        text += case_markdown(by_id[key])
    text += "## Fresh independent audit\n\nThe fresh audit reruns all seven prior counterexamples. Six now pass after repairs against existing rules; normal sampling remains a failed implementation policy.\n\n"
    text += markdown_table(["Affected behavior", "Fresh audit result"], issues) + "\n\n"
    text += "Repair the remaining normal issue against the existing proposed rules. Flag genuinely missing meaning separately. Do not make a shortcut normative simply because both readers used it. The audit's static batch-operation concern was not reproduced and is not counted as an eighth confirmed issue.\n\n"
    text += "[Independent audit](delivery/independent-audit.json) · [Diagnostic results](delivery/audit-diagnostics.json)\n\n"
    text += "## Supporting cases\n\n<details>\n<summary>Colorado, railway and animation demonstrations</summary>\n\n"
    for key in ["colorado", "railway", "animation"]:
        text += case_markdown(by_id[key])
    text += "</details>\n\n## Proposed choices awaiting agreement\n\n"
    text += "The group supports input-only physical placement and project adjustments versus model-local child offsets. The preferred HPR input and detailed chart, carrier and export conventions await adoption. Proposed definitions, adoption and implementation coverage are separate assessments.\n\n"
    text += markdown_table(["Placement topic", "Proposed meaning to review"], placement_choices) + "\n\n" + markdown_table(["Data or declaration topic", "Proposed meaning to review"], data_choices) + "\n\n"
    text += "Coordinate epochs and scene-authored operation/resource controls remain deferred without foreclosing later support. Regional and global workflows remain represented.\n\n"
    text += "## Detailed evidence\n\n<details>\n<summary>Reader comparisons, consumer coverage and provenance</summary>\n\n" + markdown_table(["Path or check", "Recorded evidence"], evidence_rows) + "\n\n"
    for key, example in base["examples"].items():
        text += f"### {key}: {example['source_label']} to {example['target_label']} ({example['unit']})\n\n"
        rows = [[label, *(f"{example[name][i]:,.8f}" for name in ["source", "python", "native", "ov"])] for i, label in enumerate(["Map east coordinate", "Map north coordinate", "Height"])]
        text += markdown_table(["Component", "Source", "Python", "C++", "OV-hosted Python"], rows) + "\n\n"
    text += "There are two placement readers. Omniverse reuses Python with a verified stage geometry sink. Hydra consumes a C++-resolved ordinary USD bake. Shared libraries do not establish independent geodetic validation. This run establishes no Omniverse rendering, physics integration, general coordinate-bearing primvar coverage or geospatial Hydra filter.\n\n"
    text += "Bounds for the returned polygonal geometry cover its vertices and straight faces. They do not certify the continuous image of an original curved surface or behavior between exported time samples. These remain implementation and verification limits.\n\n"
    text += f"Executed proposal SHA-256: `{base['proposal_sha256']}`. Immutable receipt SHA-256: `{base['immutable_receipt_sha256']}`. The exact candidate text and diff remain in `proposal/`; derived explanations add no normative authority.\n\n"
    text += "[Receipt](delivery/run-report.json) · [Requirement trace](proposal-quality.json) · [Integration evidence](delivery/integration-evidence.json) · [Exact child-transform comparison](delivery/transform-order-comparison.json)\n\n</details>\n\n"
    text += "## Sources and reproduction\n\nThe Eiffel mesh is `( FREE ) La tour Eiffel` by [SDC PERFORMANCE](https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674), under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The examples reorient and render it with illustrative context. Partner-data credit and permission remain in `data/README.md` and `data/LICENSE-partner.txt`.\n\n"
    text += "`run.py` executes a fresh run with pinned inputs and dependencies. `collateral/derive_contract_delivery.py` binds the assessment to that receipt, the proposal and a later audit, then derives this README and its slide story. `collateral/contract_slides.mjs` uses the same assessment sentences and recorded data. `collateral/verify_contract_delivery.py` checks the actual artifacts and the audience review record. [Delivery guidance](collateral/README.md) explains the required human-oriented assessment and visual review.\n"
    (root / "README.md").write_text(text, encoding="utf-8", newline="\n")

    descriptions = {
        "author_review": "Detailed candidate choices still need group review. Matching prototype results do not establish agreement.",
        "known_issues": f"{len(unresolved)} unresolved audit issue limits implementation coverage; six prior defects pass fresh counterexamples.",
        "consumer_boundary": "Two placement readers. OV reuses Python, and Hydra consumes a bake. No third independent engine or full conformance is established.",
    }
    # The renderer uses sentences and tables that occur in this generated README.
    # It does not invent a second presentation-only technical narrative.
    story = dict(base)
    story.update(
        readme_sha256=sha(root / "README.md"),
        narrative_version=1,
        audience=assessment["audience"],
        purpose=assessment["purpose"],
        opening=assessment["opening"],
        assessment=assessment["assessment"],
        summary=assessment["summary"],
        cases=cases,
        status_rows=status_rows,
        input_rows=inputs,
        issue_rows=issues,
        placement_choice_rows=placement_choices,
        data_choice_rows=data_choices,
        evidence_rows=evidence_rows,
        audit_sha256=sha(audit_path),
        assessment_sha256=sha(assessment_path),
        provenance_disposition=assessment["provenance_disposition"],
        run_comparison=assessment.get("comparison"),
        main_slide_count=8,
        appendix_slide_count=6,
        required_native_table_slides=[2, 5, 8, 12, 13, 14],
        required_native_chart_slides=[11],
        slides=[
            {"title": "Geospatial proposal assessment", "section": "Assessment of the proposal", "kind": "assessment"},
            *({"title": by_id[key]["title"], "section": by_id[key]["title"], "case": key, "kind": by_id[key]["kind"]} for key in ["inputs", "coordinates", "adjustments", "readers", "bake", "measurements"]),
            {"title": "Fresh independent audit", "section": "Fresh independent audit", "kind": "audit"},
            *({"title": "Appendix: " + by_id[key]["title"], "section": by_id[key]["title"], "case": key, "kind": by_id[key]["kind"]} for key in ["colorado", "railway", "animation"]),
            {"title": "Appendix: Placement choices under review", "section": "Proposed choices awaiting agreement", "kind": "placement_choices"},
            {"title": "Appendix: Data and declaration choices", "section": "Proposed choices awaiting agreement", "kind": "data_choices"},
            {"title": "Appendix: Evidence and its limits", "section": "Detailed evidence", "kind": "evidence"},
        ],
    )
    (root / "delivery/story.json").write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    pr = "This run assesses whether another implementer can derive the proposed geospatial behavior without guessing source data or evaluation rules. The README and slides explain each demonstration's expected result, observed behavior and limits, with illustrations distinguished from executed evidence.\n\nThe candidate now specifies the exercised inputs and rules, but detailed choices still need group review. Six prior audit defects pass fresh counterexamples; normal-domain sampling remains unresolved. Selected reader comparisons, ordinary USD bakes and native-data cases work. Shared PROJ and decoding limit independent verification, and whole-proposal conformance is not established.\n\nSee the example README, proposal snapshot and audit for the current assessment, review choices and evidence. " + assessment["provenance_disposition"] + "\n"
    if assessment.get("comparison"):
        comparison = json.loads((root / "delivery/run-comparison.json").read_text(encoding="utf-8"))
        pr = assessment["assessment"] + "\n\n" + assessment["comparison"]["explanation"] + "\n\n"
        pr += f"Fresh execution: {base['tests']['regressions_passed']} regression checks and {base['tests']['distinguishing_controls_passed']} distinguishing controls passed. All {len(comparison['numeric_case_comparisons'])} recorded numerical case comparisons across both placement readers and the Omniverse geometry sink pass their existing acceptance limits; {sum(c['exactly_equal'] for c in comparison['numeric_case_comparisons'])} are exactly equal. Six prior audit defects pass fresh counterexamples after clause-traced repairs; normal sampling remains unresolved. Whole-proposal conformance is not claimed.\n\n"
        pr += "The README and slides pair the working demonstrations with their proposal meaning and limits. Detailed candidate choices still need group review. Shared PROJ and dataset decoding limit independent verification.\n\n" + assessment["provenance_disposition"] + "\n"
    (root / "delivery/pr-body.md").write_text(pr, encoding="utf-8", newline="\n")
    assert not re.search(r"https://github.com/(?:PixarAnimationStudios/OpenUSD|[^/]+/OpenUSD-proposals)/(?:pull|issues)/", text + pr)
    validate_narrative(root, story)
    return story


def validate_narrative(root, story):
    """Necessary structural checks, not an automated proof of comprehension."""
    root = Path(root)
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert story["readme_sha256"] == sha(root / "README.md")
    assert story["main_slide_count"] + story["appendix_slide_count"] == len(story["slides"])
    assert {c['id'] for c in story['cases']} == {'inputs','coordinates','adjustments','readers','bake','measurements','colorado','railway','animation'}
    assert story["audience"] and story["purpose"]
    assert "## Assessment of the proposal" in readme
    assert readme.index("## Assessment of the proposal") < readme.index("## Detailed evidence")
    assert "complete proposed answer for every" not in readme.lower()
    for case in story["cases"]:
        assert case["requirement_ids"] and case["clause_heading"]
        for field in ["question", "rule", "expected", "observed", "implication", "boundary"]:
            assert case.get(field) and case[field] in readme, (case["id"], field, "Not derived from README")
        if case.get("image"):
            assert f"delivery/{case['image']['path']}" in readme
            assert case["image"]["role"] in readme.lower()
    assert len(story["issue_rows"]) == 7
    for rows in [story['issue_rows'],story['status_rows'],story['placement_choice_rows'],story['data_choice_rows'],story['evidence_rows']]:
        for row in rows:
            assert all(cell in readme for cell in row)
    if (root / 'delivery/run-comparison.json').exists():
        comparison=json.loads((root / 'delivery/run-comparison.json').read_text(encoding='utf-8'))
        records=comparison['numeric_case_comparisons']
        assert not comparison['numeric_regressions']
        pr=(root / 'delivery/pr-body.md').read_text(encoding='utf-8')
        assert f"{sum(c['exactly_equal'] for c in records)} are exactly equal" in pr
        if not all(c['exactly_equal'] for c in records):
            assert 'exactly match the prior run' not in pr, 'Review body overstates previous-run equality'
    assert "Omniverse live geometry" not in readme and "Omniverse live stage" not in readme
    assert "readability" not in story.get("automatic_pass_claim", "").lower()
    return {"structural_assessment_checks_passed": True, "claim": "Each case has sourced expectation, observation, interpretation and limits. Human-oriented clarity still requires explicit inspection of rendered artifacts."}


def verify_assessment_controls(root, story):
    """Exercise omissions and stale authorities that previously escaped delivery."""
    import copy
    import tempfile
    root=Path(root)
    proof=validate_narrative(root,story)
    rejected=[]
    def reject(label, action):
        try: action()
        except AssertionError: rejected.append(label)
        else: raise AssertionError('Accepted invalid delivery assessment: '+label)
    for label,change in [
        ('Missing evidence limit',lambda x:x['cases'][0].update(boundary='')),
        ('Omitted later audit issue',lambda x:x['issue_rows'].pop()),
        ('Omitted demonstration assessment',lambda x:x['cases'].pop()),
        ('Stale README story',lambda x:x.update(readme_sha256='0'*64)),
    ]:
        bad=copy.deepcopy(story);change(bad)
        reject(label,lambda:validate_narrative(root,bad))
    assessment=json.loads((root/'collateral/delivery-assessment.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='geospatial-assessment-') as temp:
        for key,label in [('proposal_sha256','Changed proposal authority'),('execution_receipt_sha256','Changed execution receipt'),('audit_source_sha256','Changed later audit')]:
            bad=copy.deepcopy(assessment);bad[key]='0'*64
            path=Path(temp)/'bad.json';path.write_text(json.dumps(bad),encoding='utf-8')
            reject(label,lambda:prepare(root,story,path,root/'delivery/independent-audit.json'))
        bad=copy.deepcopy(assessment);bad['cases'][0]['clause_heading']='### Invented authority'
        path=Path(temp)/'bad.json';path.write_text(json.dumps(bad),encoding='utf-8')
        reject('Invented proposal clause',lambda:prepare(root,story,path,root/'delivery/independent-audit.json'))
    proof.update(rejected_controls=rejected,automatic_checks_prove_comprehension=False)
    return proof
