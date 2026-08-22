#!/usr/bin/env python3
"""Fail when the built Inspect site contains private or cross-paper material."""
from __future__ import annotations

import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else SITE / "_site"
FORBIDDEN_FILE = SITE / "FORBIDDEN.txt"
TEXT_SUFFIXES = {".html", ".svg", ".css", ".js"}
FORBIDDEN_ARTIFACT_SUFFIXES = {".bib", ".bbl", ".doc", ".docx", ".pdf", ".tex", ".zip"}
ALLOW = (
    "github.com/PeterPonyu/inspect-gate",
    "peterponyu.github.io/inspect-gate",
)


def strip_allowed(text: str) -> str:
    for needle in ALLOW:
        text = text.replace(needle, "")
    return text


def main() -> int:
    patterns = [
        line.strip()
        for line in FORBIDDEN_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    text_files = [path for path in ROOT.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES]
    if not text_files:
        print(f"no built text assets under {ROOT}")
        return 1

    hits: list[str] = []
    for path in text_files:
        rel = path.relative_to(ROOT)
        text = strip_allowed(path.read_text(encoding="utf-8", errors="replace"))
        for pattern in patterns:
            if pattern in text:
                hits.append(f"{rel}: {pattern}")
        if re.search(r"\\(?:cite|ref|cref)\b", text):
            hits.append(f"{rel}: TeX cite/ref token")

    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in FORBIDDEN_ARTIFACT_SUFFIXES:
            hits.append(f"{path.relative_to(ROOT)}: forbidden submission artifact")

    if hits:
        print("leak/artifact gate failed:\n  " + "\n  ".join(sorted(hits)))
        return 1
    print(f"leak/artifact gate clean ({len(text_files)} text assets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
