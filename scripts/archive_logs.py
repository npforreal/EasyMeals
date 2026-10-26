"""Lưu trữ phần cũ của PROGRESS.md, REVIEW.md, PLAN.md vào thư mục archive/ để agent đỡ phải đọc.

Chạy khi KẾT THÚC MỘT GIAI ĐOẠN (xem AGENTS.md). Không xoá nội dung nào: phần cũ được chuyển
nguyên văn sang archive/PROGRESS.md, archive/REVIEW.md, archive/PLAN.md.

    python scripts/archive_logs.py             # giữ 3 mục PROGRESS, 2 mục REVIEW mới nhất
    python scripts/archive_logs.py --dry-run   # chỉ báo sẽ chuyển gì

Quy ước: PROGRESS.md thêm mục mới ở ĐẦU tệp (mới nhất trước); REVIEW.md và PLAN.md thêm ở CUỐI.
PLAN.md: chỉ lưu trữ mục đã xong hoàn toàn (không còn "- [ ]") và không phải mục cuối.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = ROOT / "archive"


def split_sections(text: str) -> tuple[str, list[str]]:
    """Tách phần đầu tệp và các mục bắt đầu bằng '## '."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not starts:
        return text, []
    preamble = "".join(lines[: starts[0]])
    sections = ["".join(lines[a:b]) for a, b in zip(starts, [*starts[1:], len(lines)], strict=True)]
    return preamble, sections


def title(section: str) -> str:
    return section.splitlines()[0].removeprefix("## ").strip()


def _pointer(preamble: str, archive_name: str) -> str:
    note = f"> Lịch sử cũ nằm trong `archive/{archive_name}` (chỉ đọc khi cần tra cứu).\n"
    if note in preamble:
        return preamble
    return preamble.rstrip("\n") + "\n\n" + note + "\n"


def _write_archive(name: str, moved: list[str], newest_first: bool) -> None:
    ARCHIVE_DIR.mkdir(exist_ok=True)
    path = ARCHIVE_DIR / name
    header = f"# Lưu trữ {name} (nguyên văn, không chỉnh sửa)\n\n"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    body = existing.removeprefix(header)
    new = "".join(moved)
    path.write_text(header + (new + body if newest_first else body + new), encoding="utf-8")


def archive_progress(keep: int, dry: bool) -> list[str]:
    path = ROOT / "PROGRESS.md"
    preamble, sections = split_sections(path.read_text(encoding="utf-8"))
    kept, moved = sections[:keep], sections[keep:]
    if moved and not dry:
        _write_archive("PROGRESS.md", moved, newest_first=True)
        path.write_text(_pointer(preamble, "PROGRESS.md") + "".join(kept), encoding="utf-8")
    return [title(s) for s in moved]


def archive_review(keep: int, dry: bool) -> list[str]:
    path = ROOT / "REVIEW.md"
    preamble, sections = split_sections(path.read_text(encoding="utf-8"))
    cut = max(len(sections) - keep, 0)
    moved, kept = sections[:cut], sections[cut:]
    if moved and not dry:
        _write_archive("REVIEW.md", moved, newest_first=False)
        path.write_text(_pointer(preamble, "REVIEW.md") + "".join(kept), encoding="utf-8")
    return [title(s) for s in moved]


def _is_done(section: str) -> bool:
    return "- [x]" in section and "- [ ]" not in section


def split_subsections(section: str) -> tuple[str, list[str]]:
    """Tách phần đầu của một mục '## ' và các mục con '### '."""
    lines = section.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith("### ")]
    if not starts:
        return section, []
    ends = [*starts[1:], len(lines)]
    head = "".join(lines[: starts[0]])
    return head, ["".join(lines[a:b]) for a, b in zip(starts, ends, strict=True)]


DONE_PHASES_PREFIX = "> Giai đoạn đã xong và lưu trữ (xem `archive/PLAN.md`): "


def _archive_done_phases(last: str) -> tuple[str, list[str]]:
    """Chuyển các '### Giai đoạn ...' đã xong ở mục cuối; trả (mục mới, danh sách đã chuyển)."""
    head, subs = split_subsections(last)
    moved = [x for x in subs if x.startswith("### Giai đoạn") and _is_done(x)]
    if not moved:
        return last, []
    kept = [x for x in subs if x not in moved]
    names = [x.splitlines()[0].removeprefix("### ").split(" — ")[0] for x in moved]
    old = [ln for ln in head.splitlines() if ln.startswith(DONE_PHASES_PREFIX)]
    if old:
        names = [n for n in old[0].removeprefix(DONE_PHASES_PREFIX).split(", ") if n] + names
        head = "".join(
            ln for ln in head.splitlines(keepends=True) if ln not in (old[0], old[0] + "\n")
        )
    head = head.rstrip("\n") + "\n\n" + DONE_PHASES_PREFIX + ", ".join(names) + "\n\n"
    return head + "".join(kept), moved


def archive_plan(dry: bool) -> list[str]:
    path = ROOT / "PLAN.md"
    preamble, sections = split_sections(path.read_text(encoding="utf-8"))
    if len(sections) < 2:
        return []
    index_title = "## Đã hoàn thành và lưu trữ"
    candidates = [x for x in sections[:-1] if not x.startswith(index_title)]
    moved = [x for x in candidates if "- [ ]" not in x]
    kept = [x for x in sections[:-1] if x not in moved]
    new_last, moved_phases = _archive_done_phases(sections[-1])
    kept.append(new_last)
    if (moved or moved_phases) and not dry:
        _write_archive("PLAN.md", [*moved, *moved_phases], newest_first=False)
        index = "## Đã hoàn thành và lưu trữ (xem `archive/PLAN.md`)\n\n" + "".join(
            f"- {title(x)}\n" for x in moved
        )
        previous = [x for x in kept if x.startswith("## Đã hoàn thành và lưu trữ")]
        if previous:  # gộp mục lục cũ
            old_lines = previous[0].splitlines(keepends=True)[2:]
            index += "".join(line for line in old_lines if line.strip())
            kept = [x for x in kept if x not in previous]
        path.write_text(
            _pointer(preamble, "PLAN.md") + index + "\n" + "".join(kept), encoding="utf-8"
        )
    return [title(x) for x in moved] + [
        x.splitlines()[0].removeprefix("### ") for x in moved_phases
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep-progress", type=int, default=3)
    parser.add_argument("--keep-review", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    for label, moved in (
        ("PROGRESS.md", archive_progress(args.keep_progress, args.dry_run)),
        ("REVIEW.md", archive_review(args.keep_review, args.dry_run)),
        ("PLAN.md", archive_plan(args.dry_run)),
    ):
        verb = "sẽ chuyển" if args.dry_run else "đã chuyển"
        print(f"{label}: {verb} {len(moved)} mục")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
