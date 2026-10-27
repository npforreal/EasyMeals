#!/usr/bin/env python3
"""Kiểm tra số phiên bản app đồng bộ giữa Web, API, Android và iOS (xem docs/release.md).

Thoát mã 1 nếu có nơi lệch phiên bản. Chạy: python scripts/check_version.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (tệp, regex lấy phiên bản; nhóm 1 là số phiên bản)
SOURCES: list[tuple[str, str]] = [
    ("package.json", r'"version":\s*"([^"]+)"'),
    ("pyproject.toml", r'(?m)^version\s*=\s*"([^"]+)"'),
    ("app/main.py", r'version="([^"]+)"'),
    ("app/static/js/storage.js", r'APP_VERSION\s*=\s*"([^"]+)"'),
    ("mobile/android/app/build.gradle.kts", r'versionName\s*=\s*"([^"]+)"'),
    (
        "mobile/android/app/src/main/java/com/easymeals/app/data/backup/BackupManager.kt",
        r'const val APP_VERSION\s*=\s*"([^"]+)"',
    ),
    ("mobile/ios/project.yml", r'MARKETING_VERSION:\s*"([^"]+)"'),
    (
        "mobile/ios/EasyMeals/Data/Backup/BackupManager.swift",
        r'static let appVersion\s*=\s*"([^"]+)"',
    ),
]


def main() -> int:
    found: dict[str, str] = {}
    for rel, pattern in SOURCES:
        match = re.search(pattern, (ROOT / rel).read_text(encoding="utf-8"))
        if not match:
            print(f"Không đọc được phiên bản trong {rel}", file=sys.stderr)
            return 1
        found[rel] = match.group(1)
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    found["package-lock.json"] = lock["version"]

    versions = set(found.values())
    if len(versions) != 1:
        print("Phiên bản không đồng bộ:", file=sys.stderr)
        for rel, ver in found.items():
            print(f"  {ver:10} {rel}", file=sys.stderr)
        return 1
    print(f"Phiên bản đồng bộ: {versions.pop()} ({len(found)} nơi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
