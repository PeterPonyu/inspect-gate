#!/usr/bin/env python3
"""Validate Inspect Pages routes, project prefix, and local links after build."""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "_site"
PREFIX = "/inspect-gate/"
ROUTES = (
    "index.html",
    "gate/index.html",
    "certificate/index.html",
    "envelope/index.html",
    "baseline/index.html",
    "honesty/index.html",
    "reproduce/index.html",
    "cite/index.html",
)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        key = "href" if tag in {"a", "link"} else "src" if tag in {"img", "script", "source"} else None
        if key is None:
            return
        for name, value in attrs:
            if name == key and value:
                self.links.append(value)


def local_target(url: str) -> Path | None:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or url.startswith(("mailto:", "tel:", "#")):
        return None
    path = unquote(parsed.path)
    if not path:
        return None
    if path.startswith("/"):
        if not path.startswith(PREFIX):
            raise ValueError(f"root-relative URL lacks {PREFIX}: {url}")
        path = path[len(PREFIX) :]
    target = ROOT / path
    if path.endswith("/") or not Path(path).suffix:
        target /= "index.html"
    return target


def main() -> int:
    failures: list[str] = []
    for route in ROUTES:
        if not (ROOT / route).is_file():
            failures.append(f"missing route: {route}")

    for html in ROOT.rglob("*.html"):
        parser = LinkParser()
        parser.feed(html.read_text(encoding="utf-8", errors="replace"))
        for url in parser.links:
            try:
                target = local_target(url)
            except ValueError as exc:
                failures.append(f"{html.relative_to(ROOT)}: {exc}")
                continue
            if target is not None and not target.exists():
                failures.append(f"{html.relative_to(ROOT)}: broken local link {url}")

    if failures:
        print("prefix/route/link gate failed:\n  " + "\n  ".join(sorted(set(failures))))
        return 1
    print(f"prefix/route/link gate clean ({len(list(ROOT.rglob('*.html')))} HTML files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
