#!/usr/bin/env python3
"""Session Handoff & Compact State Summarizer.

Generates a concise Markdown brief of the current repository state:
- Active PLAN.md round, objective, completed & pending milestones
- Most recent PROGRESS.md entries
- Git branch, recent commits, and working tree status
- Ideal for pasting into a new conversation or before running `/compact`.

Usage:
    python scripts/handoff.py
    python scripts/handoff.py --output handoff.md
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_repo_root(start_dir: Path | None = None) -> Path:
    current = (start_dir or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists() or (parent / "PLAN.md").exists():
            return parent
    return current


def run_cmd(cmd: list[str], cwd: Path) -> str:
    try:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return res.stdout.strip()
    except Exception:
        return ""


def get_active_plan_round(root: Path) -> str:
    plan_path = root / "PLAN.md"
    if not plan_path.exists():
        return "No `PLAN.md` found."

    lines = plan_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not starts:
        return "No active round found in `PLAN.md`."

    last_round_lines = lines[starts[-1] :]
    return "\n".join(last_round_lines[:40])


def get_recent_progress(root: Path, max_lines: int = 35) -> str:
    progress_path = root / "PROGRESS.md"
    if not progress_path.exists():
        return "No `PROGRESS.md` found."

    lines = progress_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not starts:
        return "\n".join(lines[:max_lines])

    return "\n".join(lines[starts[0] : starts[0] + max_lines])


def get_git_summary(root: Path) -> dict[str, str]:
    branch = run_cmd(["git", "branch", "--show-current"], root) or "unknown"
    commits = run_cmd(["git", "log", "-n", "3", "--oneline"], root) or "no commits"
    status = run_cmd(["git", "status", "--short"], root)
    if not status:
        status = "Clean (no uncommitted changes)"
    return {
        "branch": branch,
        "commits": commits,
        "status": status,
    }


def generate_handoff_brief(root: Path) -> str:
    git_info = get_git_summary(root)
    active_plan = get_active_plan_round(root)
    recent_progress = get_recent_progress(root)

    return f"""# Session Handoff Brief

## Repository & Git Context
- **Root**: `{root.name}`
- **Active Branch**: `{git_info["branch"]}`
- **Recent Commits**:
```text
{git_info["commits"]}
```
- **Working Tree Status**:
```text
{git_info["status"]}
```

---

## Active Plan Round (from `PLAN.md`)
```markdown
{active_plan}
```

---

## Latest Progress (from `PROGRESS.md`)
```markdown
{recent_progress}
```
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate session handoff brief")
    parser.add_argument("--repo-path", type=Path, default=None, help="Repository root path")
    parser.add_argument(
        "--output", "-o", type=Path, default=None, help="Save summary to output file"
    )
    args = parser.parse_args()

    root = find_repo_root(args.repo_path)
    brief = generate_handoff_brief(root)

    if args.output:
        args.output.write_text(brief, encoding="utf-8")
        print(f"Handoff brief saved to: {args.output}")
    else:
        print(brief)

    return 0


if __name__ == "__main__":
    sys.exit(main())
