"""Profiles summaries and conservative publication maintenance.

Consumer summary reads do not load payloads. Publication validation inspects
retained content and variants; native ClaimsAPI authors the actual token types.
The capability/profile identities remain proposed rather than approved.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from pxr import Usd, Sdf
from common import ROOT, CAPABILITY, PROFILE, require
from placement import direct


def profile_summary(stage):
    p = stage.GetDefaultPrim()
    d = p.GetCustomDataByKey("profilesInfo") or {}
    usages = d.get("capabilityUsages")
    compat = d.get("profileCompatibility", {})
    ap = p.GetMetadata("apiSchemas")
    complete = (
        ap is not None
        and "ClaimsAPI" in ap.GetAppliedItems()
        and isinstance(usages, dict)
        and PROFILE in compat
        and not compat[PROFILE]
    )
    hard = isinstance(usages, dict) and usages.get(CAPABILITY) == "hard"
    return {
        "coverage": (
            "complete-positive"
            if complete and hard
            else "complete-empty" if complete else "unknown"
        ),
        "requiresResolution": True if hard else False if complete else None,
    }


def publish_claim(stage, requires=True, complete=True):
    # The native existing ClaimsAPI authors the exact VtToken/VtTokenArray types.
    # Python 26.5 lacks these bindings: a lookalike string dictionary is NOT proof.
    stage.GetRootLayer().Save()
    request = {
        "publishStage": stage.GetRootLayer().realPath,
        "requires": requires,
        "complete": complete,
    }
    env = os.environ.copy()
    env["PATH"] = (
        "C:/git/usd-geospatial-fresh/inst/bin;C:/git/usd-geospatial-fresh/inst/lib;C:/Users/aluk/AppData/Local/Programs/Python/Python310;C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-proj-tiff/bin;"
        + env["PATH"]
    )
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "request.json"
        dest = Path(td) / "result.json"
        src.write_text(json.dumps(request))
        cmd = [
            str(ROOT / "native/build/resolve.exe"),
            str(src),
            str(dest),
            str(ROOT / "schema"),
        ]
        completed = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=60
        )
        require(
            completed.returncode == 0,
            "native Profiles publication failed ("
            + str(completed.returncode)
            + "): "
            + completed.stderr,
        )
    stage.GetRootLayer().Reload(True)


def validate_publication(stage):
    summary = profile_summary(stage)
    if summary["requiresResolution"] is True:
        return summary
    # Inspect all retained variants in private sessions at publication time.
    # Consumer summary reads never invoke this traversal or load any payload.
    session = Sdf.Layer.CreateAnonymous()
    session.TransferContent(stage.GetSessionLayer())
    pending = [session]
    seen = set()
    dependent = False
    while pending:
        current = pending.pop()
        signature = current.ExportToString()
        if signature in seen:
            continue
        seen.add(signature)
        require(
            len(seen) <= 4096,
            "coverage unknown: too many variant combinations; retain hard usage",
        )
        copy = Usd.Stage.Open(stage.GetRootLayer(), current, load=Usd.Stage.LoadAll)
        require(
            not copy.GetCompositionErrors(),
            "coverage unknown: unresolved composition; retain hard usage",
        )
        for p in copy.TraverseAll():
            dependent = (
                dependent or direct(p) or p.GetTypeName() == "GeospatialDataSource"
            )
            require(not dependent, "stale or missing dependency summary")
            for name in p.GetVariantSets().GetNames():
                v = p.GetVariantSet(name)
                for choice in v.GetVariantNames():
                    if choice == v.GetVariantSelection():
                        continue
                    next_session = Sdf.Layer.CreateAnonymous()
                    next_session.TransferContent(current)
                    candidate = Usd.Stage.Open(
                        stage.GetRootLayer(), next_session, load=Usd.Stage.LoadAll
                    )
                    candidate.SetEditTarget(next_session)
                    candidate.GetPrimAtPath(p.GetPath()).GetVariantSet(
                        name
                    ).SetVariantSelection(choice)
                    if next_session.ExportToString() not in seen:
                        pending.append(next_session)
    return summary
