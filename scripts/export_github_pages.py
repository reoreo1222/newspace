#!/usr/bin/env python3
"""Export the local Newspace WordPress site as a portable GitHub Pages snapshot.

The generated site uses relative links, so it works both at a repository path such
as /newspace-preview/ and on a custom domain. The output is intentionally noindex
and disables the WordPress-backed contact submission.
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup


DEFAULT_ROUTES = (
    "/",
    "/services/",
    "/services/facade/",
    "/services/energy/",
    "/services/cleaning/",
    "/services/water/",
    "/works/",
    "/news/",
    "/about/",
    "/contact/",
    "/privacy-policy/",
)

SKIP_LINK_RELS = {"canonical", "shortlink", "EditURI"}
LOCAL_ASSET_PREFIXES = ("/wp-content/", "/wp-includes/")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "NewspaceStaticExporter/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def static_route(route: str) -> str:
    parts = urllib.parse.urlsplit(route)
    page = urllib.parse.parse_qs(parts.query).get("works_page", ["1"])[0]
    if parts.path == "/works/" and page.isdigit() and int(page) > 1:
        return f"/works/page/{int(page)}/"
    return parts.path


def discover_routes(source: str) -> list[str]:
    routes = list(DEFAULT_ROUTES)
    for route in routes:
        soup = BeautifulSoup(fetch(source + route), "html.parser")
        for link in soup.select("a[href]"):
            parts = urllib.parse.urlsplit(urllib.parse.urljoin(source + route, link["href"]))
            if parts.netloc != urllib.parse.urlsplit(source).netloc:
                continue
            if not parts.path.startswith(("/works/", "/news/")):
                continue
            candidate = parts.path
            page = urllib.parse.parse_qs(parts.query).get("works_page", ["1"])[0]
            if parts.path == "/works/" and page.isdigit() and int(page) > 1:
                candidate += f"?works_page={int(page)}"
            if candidate not in routes:
                routes.append(candidate)
    return routes


def output_file_for_route(output: Path, route: str) -> Path:
    route = static_route(route)
    route_path = urllib.parse.unquote(urllib.parse.urlsplit(route).path).strip("/")
    return output / route_path / "index.html" if route_path else output / "index.html"


def relative_reference(page_file: Path, output: Path, target_path: str, query: str = "", fragment: str = "") -> str:
    target_path = urllib.parse.unquote(target_path)
    is_directory = target_path.endswith("/") or target_path == ""
    target = target_path.strip("/")
    start = page_file.parent.relative_to(output).as_posix() or "."
    relative = posixpath.relpath(target or ".", start)
    if is_directory and not relative.endswith("/"):
        relative += "/"
    if relative == "./" and not is_directory:
        relative = "."
    return relative + (("?" + query) if query else "") + (("#" + fragment) if fragment else "")


def is_local_url(parts: urllib.parse.SplitResult, source_netloc: str) -> bool:
    return (not parts.netloc and not parts.scheme) or parts.netloc == source_netloc


def download_asset(source: str, source_origin: str, output: Path, path: str) -> None:
    clean_path = urllib.parse.unquote(path).lstrip("/")
    destination = output / clean_path
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.write_bytes(fetch(urllib.parse.urljoin(source_origin + "/", path.lstrip("/"))))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download asset {path}: {exc}") from exc


def rewrite_url(value: str, page_file: Path, output: Path, source_origin: str, source_netloc: str) -> str:
    value = value.strip()
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return value
    parts = urllib.parse.urlsplit(value)
    if not is_local_url(parts, source_netloc):
        return value
    path = static_route(value) or "/"
    query = "" if "works_page" in urllib.parse.parse_qs(parts.query) else parts.query
    if path.startswith(LOCAL_ASSET_PREFIXES):
        download_asset(value, source_origin, output, path)
    return relative_reference(page_file, output, path, query, parts.fragment)


def rewrite_srcset(value: str, page_file: Path, output: Path, source_origin: str, source_netloc: str) -> str:
    rewritten = []
    for item in value.split(","):
        bits = item.strip().split()
        if bits:
            bits[0] = rewrite_url(bits[0], page_file, output, source_origin, source_netloc)
        rewritten.append(" ".join(bits))
    return ", ".join(rewritten)


def ensure_noindex(soup: BeautifulSoup) -> None:
    for meta in soup.select('meta[name="robots"]'):
        meta.decompose()
    tag = soup.new_tag("meta")
    tag["name"] = "robots"
    tag["content"] = "noindex, nofollow, noarchive"
    soup.head.append(tag)


def remove_wordpress_runtime_markup(soup: BeautifulSoup) -> None:
    for tag in list(soup.find_all("link")):
        rels = {str(item) for item in (tag.get("rel") or [])}
        href = tag.get("href", "")
        if rels & SKIP_LINK_RELS or "wp-json" in href or "oembed" in href or "xmlrpc.php" in href:
            tag.decompose()
    for tag in list(soup.find_all("meta")):
        if tag.get("name") == "generator":
            tag.decompose()
        elif tag.get("property") == "og:url":
            tag.decompose()
    for tag in list(soup.find_all("script")):
        script_type = tag.get("type", "")
        script_id = tag.get("id", "")
        src = tag.get("src", "")
        script_text = tag.string or ""
        if (
            script_type in {"application/ld+json", "speculationrules"}
            or "emoji" in script_id
            or "wp-emoji" in src
            or "wpemoji" in script_text.lower()
            or "wp-emoji" in script_text.lower()
            or "contact-form-7" in src
            or "wpcf7" in script_id
            or "wpcf7" in script_text
            or "swv" in script_id
        ):
            tag.decompose()
    for tag in list(soup.find_all("style")):
        style_id = tag.get("id", "")
        style_text = tag.string or ""
        if "emoji" in style_id.lower() or "wp-emoji" in style_text.lower():
            tag.decompose()


def export_page(route: str, source_origin: str, output: Path) -> None:
    page_file = output_file_for_route(output, route)
    page_file.parent.mkdir(parents=True, exist_ok=True)
    html = fetch(urllib.parse.urljoin(source_origin + "/", route.lstrip("/"))).decode("utf-8", "replace")
    soup = BeautifulSoup(html, "html.parser")
    source_netloc = urllib.parse.urlsplit(source_origin).netloc

    remove_wordpress_runtime_markup(soup)
    ensure_noindex(soup)

    for style in soup.find_all("style"):
        if style.string:
            style.string = re.sub(
                r"url\((['\"]?)([^)'\"]+)\1\)",
                lambda match: "url('" + rewrite_url(match.group(2), page_file, output, source_origin, source_netloc) + "')",
                str(style.string),
            )

    for tag in soup.find_all(True):
        for attribute in ("href", "src", "poster"):
            if tag.has_attr(attribute):
                tag[attribute] = rewrite_url(tag[attribute], page_file, output, source_origin, source_netloc)
        if tag.has_attr("srcset"):
            tag["srcset"] = rewrite_srcset(tag["srcset"], page_file, output, source_origin, source_netloc)
        if tag.has_attr("style"):
            tag["style"] = re.sub(
                r"url\((['\"]?)(https?://127\.0\.0\.1:4180)?(/[^)'\"]+)\1\)",
                lambda match: f"url('{rewrite_url((match.group(2) or '') + match.group(3), page_file, output, source_origin, source_netloc)}')",
                tag["style"],
            )

    for form in soup.select("form.ns-contact-form"):
        form["action"] = "#"
        form["data-static-preview"] = "true"
        for hidden in form.select('input[type="hidden"]'):
            hidden.decompose()
        form.attrs.pop("novalidate", None)

    preview_css = soup.new_tag("link", rel="stylesheet", href=relative_reference(page_file, output, "/preview.css"))
    soup.head.append(preview_css)
    preview_script = soup.new_tag("script", src=relative_reference(page_file, output, "/preview.js"))
    soup.body.append(preview_script)

    rendered = str(soup)
    if not rendered.lstrip().lower().startswith("<!doctype"):
        rendered = "<!doctype html>\n" + rendered
    page_file.write_text(rendered, encoding="utf-8")


def copy_theme_assets(project_root: Path, output: Path) -> None:
    theme_source = project_root / "wordpress" / "theme" / "newspace"
    theme_target = output / "wp-content" / "themes" / "newspace"
    shutil.copytree(theme_source / "static", theme_target / "static", dirs_exist_ok=True)
    shutil.copy2(theme_source / "wordpress.css", theme_target / "wordpress.css")

    detail_css = theme_target / "static" / "service-details.css"
    if detail_css.exists():
        css = detail_css.read_text(encoding="utf-8")
        for slug in ("facade", "energy", "cleaning", "water"):
            css = css.replace(f"a[href='/services/{slug}/']", f"a[href$='/{slug}/']")
        detail_css.write_text(css, encoding="utf-8")


def write_preview_assets(output: Path) -> None:
    (output / "preview.css").write_text(
        ".github-preview-message{margin:18px 0;padding:14px 18px;border:1px solid #c7b17a;"
        "background:#f7f3e8;color:#343832;font-size:14px;line-height:1.7}\n",
        encoding="utf-8",
    )
    (output / "preview.js").write_text(
        "document.querySelectorAll('form[data-static-preview=true]').forEach(function(form){\n"
        "  form.addEventListener('submit',function(event){\n"
        "    event.preventDefault();\n"
        "    var message=form.querySelector('.github-preview-message');\n"
        "    if(!message){message=document.createElement('p');message.className='github-preview-message';"
        "message.setAttribute('role','status');form.appendChild(message);}\n"
        "    message.textContent='このサイトは確認用のため、フォームから送信できません。';\n"
        "    message.scrollIntoView({behavior:'smooth',block:'center'});\n"
        "  });\n"
        "});\n",
        encoding="utf-8",
    )
    (output / ".nojekyll").write_text("", encoding="utf-8")


def write_404(output: Path) -> None:
    html = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>ページが見つかりません | Newspace</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f7f6f2;color:#343832;font-family:serif}main{text-align:center;padding:40px}a{color:#8d7137}</style></head>
<body><main><p>404</p><h1>ページが見つかりません</h1><p><a id="home-link" href="./">トップページへ戻る</a></p></main>
<script>if(location.hostname.endsWith('github.io')){var first=location.pathname.split('/').filter(Boolean)[0];document.getElementById('home-link').href=first?'/'+first+'/':'/';}</script></body></html>"""
    (output / "404.html").write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="http://127.0.0.1:4180")
    parser.add_argument("--output", default="github-pages")
    parser.add_argument("--keep", action="store_true", help="Do not clear the output directory first")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    output = (project_root / args.output).resolve()
    if output.exists() and not args.keep:
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    copy_theme_assets(project_root, output)
    routes = discover_routes(args.source.rstrip("/"))
    for route in routes:
        print(f"Exporting {route}")
        export_page(route, args.source.rstrip("/"), output)
    write_preview_assets(output)
    write_404(output)
    print(f"Exported {len(routes)} pages to {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, urllib.error.URLError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
