"""Prepare, verify or publish a checkpoint to the owner's standing draft PR."""
import argparse
import json
from pathlib import Path
import subprocess

from geobuild.delivery import FORK, PACKAGE, prepare, verify, seal_slides

ROOT = Path(__file__).resolve().parent


def command(*args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, encoding="utf-8").strip()


def publish():
    manifest = verify(ROOT)
    git_root = Path(command("git", "rev-parse", "--show-toplevel")).resolve()
    if ROOT.relative_to(git_root).as_posix() != PACKAGE:
        raise ValueError("Publish only from the delivery package in the OpenUSD checkout.")
    remote = command("git", "remote", "get-url", "origin").removesuffix(".git")
    if remote not in (f"https://github.com/{FORK}", f"git@github.com:{FORK}"):
        raise ValueError("Origin must be the owner's OpenUSD fork.")
    branch = command("git", "branch", "--show-current")
    if branch != manifest["branch"] or branch == "dev":
        raise ValueError("Delivery branch does not match the manifest.")
    other = command("git", "status", "--porcelain", "--", ".", f":(exclude){PACKAGE}", cwd=git_root)
    if other:
        raise ValueError("Unrelated changes exist in the publishing checkout.")
    report = json.loads((ROOT / "runs" / manifest["checkpoint"] / "report.json").read_text(encoding="utf-8"))
    if report["implementation"]["source_dirty"]:
        raise ValueError("Commit the implementation, then rerun before publishing its evidence.")
    command("git", "add", "--", PACKAGE, cwd=git_root)
    if command("git", "diff", "--cached", "--name-only", cwd=git_root):
        command("git", "commit", "-m", f"usdGeospatial: deliver checkpoint {manifest['checkpoint']}", cwd=git_root)
    revision = command("git", "rev-parse", "HEAD")
    command("git", "push", "-u", "origin", branch)
    records = json.loads(command("gh", "pr", "list", "--repo", FORK, "--head", branch,
                                 "--state", "open", "--json", "number,url,isDraft,baseRefName"))
    body = str(ROOT / "docs" / "PR_BODY.md")
    if records:
        if len(records) != 1 or records[0]["baseRefName"] != "dev" or not records[0]["isDraft"]:
            raise ValueError("Existing review must be one draft against the fork's dev branch.")
        record = records[0]
        command("gh", "pr", "edit", str(record["number"]), "--repo", FORK, "--body-file", body)
        url = record["url"]
    else:
        url = command("gh", "pr", "create", "--repo", FORK, "--base", "dev", "--head", branch, "--draft",
                      "--title", "usdGeospatial: requirements-driven build and delivery loop", "--body-file", body)
    return {"repository": FORK, "branch": branch, "revision": revision, "checkpoint": manifest["checkpoint"], "url": url}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "seal-slides", "verify", "publish"))
    parser.add_argument("--run")
    parser.add_argument("--checkpoint-id")
    parser.add_argument("--pptx")
    parser.add_argument("--pdf")
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            if not args.run:
                parser.error("prepare requires --run")
            result = {"checkpoint": str(prepare(args.run, ROOT, args.checkpoint_id))}
        elif args.action == "seal-slides":
            if not args.pptx or not args.pdf:
                parser.error("seal-slides requires --pptx and --pdf")
            result = seal_slides(ROOT, args.pptx, args.pdf)
        elif args.action == "verify":
            result = verify(ROOT)
        else:
            result = publish()
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Delivery failed: {exc}\n")
