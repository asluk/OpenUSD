"""Read only the allowed proposal sections from a clean, pinned Git revision."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

PROPOSAL = "proposals/geospatial_coordinate_reference_systems/README.md"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], encoding="utf-8", errors="strict"
    ).strip()


def parse(text):
    terms = text.split("## Terms\n", 1)[1].split("## Design overview\n", 1)[0]
    functional = text.split("### Functional requirements\n", 1)[1].split("### Schema design\n", 1)[0]
    # Editing notes are instructions to authors, not functional requirements.
    body = re.sub(r"<!--.*?-->", "", functional, flags=re.S)
    starts = list(re.finditer(r"^(\d+)\. \*\*(.+?)\*\*\s*$", body, re.M))
    requirements = []
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else body.index("**What the open questions")
        block = body[match.end():end].strip()
        # A requirement sentence is the first paragraph. Cases carry no new requirement.
        sentence = " ".join(block.split("\n\n", 1)[0].split())
        case = block.split("\n\n", 1)[1] if "\n\n" in block else ""
        case = re.split(r"\n\*\*", case, maxsplit=1)[0].strip()
        requirements.append({"number": int(match[1]), "title": match[2].rstrip("."),
                             "text": sentence, "case": case,
                             "sha256": digest(match[0] + "\n" + sentence + "\n" + case)})
    questions = []
    for match in re.finditer(r"^\| (\d+) \| (.*?) \| (.*?) \|$", body, re.M):
        questions.append({"number": int(match[1]), "question": match[2], "against": match[3]})
    ids = [r["number"] for r in requirements]
    if len(ids) != len(set(ids)) or not set(range(1, 30)).issubset(ids):
        raise ValueError("Missing or duplicate frozen requirement identifiers; review extraction.")
    if [q["number"] for q in questions][:9] != list(range(1, 10)):
        raise ValueError("The nine frozen question identifiers changed; review extraction.")
    allowed = "## Terms\n" + terms.strip() + "\n\n### Functional requirements\n" + functional.strip() + "\n"
    return {"requirements": requirements, "questions": questions, "allowed_text": allowed,
            "allowed_sha256": digest(allowed)}


def snapshot(repo):
    repo = Path(repo).resolve()
    if git(repo, "status", "--porcelain", "--", PROPOSAL):
        raise ValueError("Proposal has uncommitted edits. Commit the reviewed input before a pinned run.")
    commit = git(repo, "rev-parse", "HEAD")
    text = git(repo, "show", f"{commit}:{PROPOSAL}") + "\n"
    result = parse(text)
    result.update(commit=commit, repository=str(repo), path=PROPOSAL,
                  proposal_sha256=digest(text), review_state="draft; partner approval not inferred")
    return result


def load_snapshot(path):
    """Use the checked-in, self-contained input when no proposal checkout exists."""
    result = json.loads(Path(path).read_text(encoding="utf-8"))
    allowed = result["allowed_text"]
    if digest(allowed) != result["allowed_sha256"]:
        raise ValueError("Input snapshot hash does not match its text.")
    # Parse again instead of trusting cached requirement/question records.
    wrapper = allowed.replace("### Functional requirements", "## Design overview\n\n### Functional requirements", 1)
    parsed = parse(wrapper + "\n### Schema design\n")
    if parsed["allowed_sha256"] != result["allowed_sha256"]:
        raise ValueError("Input snapshot has noncanonical sections.")
    if not re.fullmatch(r"[a-f0-9]{40}", result["commit"]):
        raise ValueError("Input snapshot needs a complete source revision.")
    result.update(parsed)
    return result
