#!/usr/bin/env python3
"""Validate the generated GitHub Pages preview without third-party packages."""

from __future__ import annotations

import re
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "github-pages"
FORBIDDEN = re.compile(r"(?:127\.0\.0\.1|localhost|admin-post\.php|wp-json|xmlrpc\.php)", re.I)


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for name in ("href", "src", "poster", "action"):
            if values.get(name):
                self.references.append(values[name] or "")
        if values.get("srcset"):
            for item in (values["srcset"] or "").split(","):
                self.references.append(item.strip().split()[0])


def local_target(page: Path, reference: str) -> Path | None:
    if not reference or reference.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
        return None
    parsed = urllib.parse.urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        return None
    route = page.relative_to(SITE).as_posix()
    base_path = "/" if route == "index.html" else f"/{page.parent.relative_to(SITE).as_posix()}/"
    resolved = urllib.parse.urlsplit(urllib.parse.urljoin(f"https://preview.invalid{base_path}", reference)).path
    target = SITE / urllib.parse.unquote(resolved.lstrip("/"))
    if resolved.endswith("/"):
        target /= "index.html"
    return target


def main() -> int:
    errors: list[str] = []
    html_files = sorted(SITE.rglob("*.html"))
    if not html_files:
        errors.append("github-pages にHTMLがありません")

    reference_count = 0
    for page in html_files:
        source = page.read_text(encoding="utf-8")
        relative = page.relative_to(SITE)
        if FORBIDDEN.search(source):
            errors.append(f"WordPressローカルURLが残っています: {relative}")
        if page.name == "index.html" and 'content="noindex, nofollow, noarchive"' not in source:
            errors.append(f"noindexがありません: {relative}")

        parser = ReferenceParser()
        parser.feed(source)
        for reference in parser.references:
            target = local_target(page, reference)
            if target is None:
                continue
            reference_count += 1
            if not target.exists():
                errors.append(f"リンク切れ: {relative} -> {reference}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"PASS: {len(html_files)} HTML files, {reference_count} local references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
