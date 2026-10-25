"""Script lưu trữ nhật ký không được làm mất nội dung và không động vào việc còn dở."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "archive_logs.py"
SPEC = importlib.util.spec_from_file_location("archive_logs", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

PROGRESS = "# log\n\n> ghi mới ở đầu\n\n## C mới\nc\n\n## B\nb\n\n## A cũ\na\n"
REVIEW = "# review\n\n## Vòng 1\n1\n\n## Vòng 2\n2\n\n## Vòng 3\n3\n"
PLAN = (
    "# plan\n\n## 1. Xong\n- [x] a\n\n## 2. Còn dở\n- [ ] b\n\n## 3. Hiện tại\nmở đầu\n\n"
    "### Giai đoạn A — xong\n- [x] a1\n\n### Giai đoạn B — dở\n- [x] b1\n- [ ] b2\n\n"
    "### Thứ tự\n1. làm A\n"
)


def _setup(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "ARCHIVE_DIR", tmp_path / "archive")
    (tmp_path / "PROGRESS.md").write_text(PROGRESS, encoding="utf-8")
    (tmp_path / "REVIEW.md").write_text(REVIEW, encoding="utf-8")
    (tmp_path / "PLAN.md").write_text(PLAN, encoding="utf-8")


def test_dry_run_changes_nothing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    mod.main(["--keep-progress", "1", "--keep-review", "1", "--dry-run"])
    assert (tmp_path / "PROGRESS.md").read_text(encoding="utf-8") == PROGRESS
    assert not (tmp_path / "archive").exists()


def test_archive_moves_old_entries_verbatim(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    mod.main(["--keep-progress", "1", "--keep-review", "1"])
    progress = (tmp_path / "PROGRESS.md").read_text(encoding="utf-8")
    assert "## C mới" in progress and "## B\n" not in progress
    archived = (tmp_path / "archive" / "PROGRESS.md").read_text(encoding="utf-8")
    assert "## B\nb\n" in archived and "## A cũ\na\n" in archived
    review = (tmp_path / "REVIEW.md").read_text(encoding="utf-8")
    assert "## Vòng 3" in review and "## Vòng 1" not in review
    assert "## Vòng 1\n1\n" in (tmp_path / "archive" / "REVIEW.md").read_text(encoding="utf-8")


def test_plan_keeps_unfinished_and_current_sections(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    mod.main(["--keep-progress", "3", "--keep-review", "3"])
    plan = (tmp_path / "PLAN.md").read_text(encoding="utf-8")
    assert "## 2. Còn dở" in plan and "- [ ] b" in plan  # còn việc dở: giữ lại
    assert "## 3. Hiện tại" in plan  # mục cuối: giữ lại
    assert "## 1. Xong" not in plan.split("Đã hoàn thành và lưu trữ", 1)[1].split("\n## ", 1)[1]
    assert "### Giai đoạn B" in plan and "### Giai đoạn A" not in plan
    assert "### Thứ tự" in plan  # mục không có checkbox không bị lưu trữ nhầm
    archived = (tmp_path / "archive" / "PLAN.md").read_text(encoding="utf-8")
    assert "## 1. Xong" in archived and "### Giai đoạn A — xong" in archived


def test_archive_is_idempotent(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    mod.main(["--keep-progress", "1", "--keep-review", "1"])
    first = {n: (tmp_path / n).read_text(encoding="utf-8") for n in ("PROGRESS.md", "PLAN.md")}
    mod.main(["--keep-progress", "1", "--keep-review", "1"])
    for name, text in first.items():
        assert (tmp_path / name).read_text(encoding="utf-8") == text
