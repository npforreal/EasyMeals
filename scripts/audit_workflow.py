#!/usr/bin/env python3
"""Project Health Check & Workflow Doctor.

Audits repository compliance with the Agentic Engineering Workflow:
- File existence: PLAN.md, PROGRESS.md, AGENTS.md, scripts/archive_logs.py, archive/
- Context discipline: file sizes of PLAN.md and PROGRESS.md (flags token bloat)
- Progress format: newest-at-top, dated entries, verification section present
- Plan hygiene: completed historical rounds not yet archived
- Quality gate: existence and executability of scripts/check.sh
- Git safety: ensures no .env or sensitive secrets are tracked

Usage:
    python scripts/audit_workflow.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MAX_PROGRESS_LINES = 150
MAX_PLAN_LINES = 250


def find_repo_root(start_dir: Path | None = None) -> Path:
    current = (start_dir or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists() or (parent / "PLAN.md").exists():
            return parent
    return current


class WorkflowAuditor:
    def __init__(self, root: Path):
        self.root = root
        self.issues: list[tuple[str, str, str]] = []  # (level, category, message)

    def log_ok(self, category: str, message: str) -> None:
        print(f"  [OK]   {category}: {message}")

    def log_warn(self, category: str, message: str) -> None:
        print(f"  [WARN] {category}: {message}")
        self.issues.append(("WARN", category, message))

    def log_fail(self, category: str, message: str) -> None:
        print(f"  [FAIL] {category}: {message}")
        self.issues.append(("FAIL", category, message))

    def check_required_files(self) -> None:
        required = [
            ("PLAN.md", "Project roadmap and active round"),
            ("PROGRESS.md", "Reverse-chronological log"),
            ("AGENTS.md", "Agent instructions & rules"),
            ("archive", "Lossless history directory"),
            ("scripts/archive_logs.py", "Log archiving automation"),
        ]
        for rel_path, desc in required:
            target = self.root / rel_path
            if target.exists():
                self.log_ok("File Check", f"`{rel_path}` present ({desc})")
            else:
                self.log_fail("File Check", f"Missing `{rel_path}` ({desc})")

    def check_context_discipline(self) -> None:
        progress_path = self.root / "PROGRESS.md"
        if progress_path.exists():
            lines = progress_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            count = len(lines)
            if count > MAX_PROGRESS_LINES:
                msg = (
                    f"PROGRESS.md is {count} lines (> {MAX_PROGRESS_LINES}). "
                    "Run `python scripts/archive_logs.py`."
                )
                self.log_warn("Token Discipline", msg)
            else:
                self.log_ok(
                    "Token Discipline",
                    f"PROGRESS.md size is lean ({count} lines <= {MAX_PROGRESS_LINES})",
                )

        plan_path = self.root / "PLAN.md"
        if plan_path.exists():
            lines = plan_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            count = len(lines)
            if count > MAX_PLAN_LINES:
                msg = (
                    f"PLAN.md is {count} lines (> {MAX_PLAN_LINES}). "
                    "Completed rounds should be archived."
                )
                self.log_warn("Token Discipline", msg)
            else:
                self.log_ok(
                    "Token Discipline", f"PLAN.md size is lean ({count} lines <= {MAX_PLAN_LINES})"
                )

    def check_progress_hygiene(self) -> None:
        path = self.root / "PROGRESS.md"
        if not path.exists():
            return

        text = path.read_text(encoding="utf-8", errors="ignore")
        sections = [s for s in text.splitlines() if s.startswith("## ")]
        if not sections:
            self.log_fail("Progress Hygiene", "PROGRESS.md has no '## ' dated entries.")
            return

        top_entry = sections[0]
        date_pattern = r"## \d{4}-\d{2}-\d{2}"
        if not re.search(date_pattern, top_entry):
            self.log_warn(
                "Progress Hygiene",
                f"Top entry '{top_entry}' does not follow '## YYYY-MM-DD — <Title>' format.",
            )
        else:
            self.log_ok("Progress Hygiene", f"Top entry format valid: {top_entry}")

        # Check verification section presence
        if "Kiểm chứng" in text or "Verification" in text or "Verified" in text:
            self.log_ok(
                "Verification Record", "PROGRESS.md includes verification evidence sections."
            )
        else:
            self.log_warn(
                "Verification Record", "No verification evidence section found in PROGRESS.md."
            )

    def check_plan_hygiene(self) -> None:
        path = self.root / "PLAN.md"
        if not path.exists():
            return

        text = path.read_text(encoding="utf-8", errors="ignore")
        rounds = [line for line in text.splitlines() if line.startswith("## ")]
        if not rounds:
            self.log_warn("Plan Hygiene", "PLAN.md has no '## Round / Đợt' sections.")
            return

        self.log_ok(
            "Plan Hygiene", f"Found {len(rounds)} round(s) in PLAN.md. Active: {rounds[-1]}"
        )

        # Check for completed historical sections not archived
        lines = text.splitlines(keepends=True)
        starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
        if len(starts) > 1:
            for i in range(len(starts) - 1):
                round_content = "".join(lines[starts[i] : starts[i + 1]])
                if "- [x]" in round_content and "- [ ]" not in round_content:
                    round_title = lines[starts[i]].strip()
                    self.log_warn(
                        "Plan Hygiene",
                        f"Round '{round_title}' is fully completed but not archived yet.",
                    )

    def check_quality_gate(self) -> None:
        check_sh = self.root / "scripts" / "check.sh"
        if check_sh.exists():
            is_exec = (check_sh.stat().st_mode & 0o111) != 0
            if is_exec:
                self.log_ok("Quality Gate", "`scripts/check.sh` exists and is executable.")
            else:
                self.log_warn(
                    "Quality Gate",
                    "`scripts/check.sh` exists but lacks execute permissions (`chmod +x`).",
                )
        else:
            self.log_warn(
                "Quality Gate",
                "No `scripts/check.sh` found. Consider setting up a fast quality gate.",
            )

    def check_git_safety(self) -> None:
        git_dir = self.root / ".git"
        if not git_dir.exists():
            return

        try:
            res = subprocess.run(
                ["git", "ls-files", ".env", "*.key", "*.pem", "*.secret"],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
            )
            tracked_secrets = [
                f for f in res.stdout.splitlines() if f and not f.endswith(".example")
            ]
            if tracked_secrets:
                self.log_fail(
                    "Git Safety", f"Sensitive files tracked in Git: {', '.join(tracked_secrets)}"
                )
            else:
                self.log_ok("Git Safety", "No tracked secret files (.env, keys) found in Git.")
        except Exception:
            pass

    def run(self) -> int:
        print(f"\nAuditing Agentic Engineering Workflow for: {self.root}")
        print("=" * 65)

        self.check_required_files()
        self.check_context_discipline()
        self.check_progress_hygiene()
        self.check_plan_hygiene()
        self.check_quality_gate()
        self.check_git_safety()

        print("=" * 65)
        fails = [i for i in self.issues if i[0] == "FAIL"]
        warns = [i for i in self.issues if i[0] == "WARN"]

        if not self.issues:
            print("Summary: ALL CHECKS PASSED. Repository is in prime workflow health!\n")
            return 0
        else:
            print(f"Summary: {len(fails)} failure(s), {len(warns)} warning(s) detected.\n")
            return 1 if fails else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit repository workflow health")
    parser.add_argument(
        "--repo-path", type=Path, default=None, help="Root path of target repository"
    )
    args = parser.parse_args()

    root = find_repo_root(args.repo_path)
    auditor = WorkflowAuditor(root)
    return auditor.run()


if __name__ == "__main__":
    sys.exit(main())
