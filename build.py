#!/usr/bin/env python3
"""Render site/templates/*.html -> dist/. Hash asset filenames.

BASE_PATH env var controls the URL prefix:
  ""              -> backend / Cloudflare Tunnel (served at root)
  "/kalolsavam"   -> GitHub Pages project site (served at /<repo>/)
"""
from __future__ import annotations
import hashlib
import os
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
DIST = ROOT / "dist"
BASE = os.environ.get("BASE_PATH", "").rstrip("/")

PAGES = [
    ("index.html", "index.html", "home"),
    ("venues.html", "pages/venues.html", "venues"),
    ("venues-location.html", "pages/venues-location.html", "venues"),
    ("venues-find.html", "pages/venues-find.html", "venues"),
    ("venues-live.html", "pages/venues-live.html", "venues"),
    ("competitions.html", "pages/competitions.html", "competitions"),
    ("photos.html", "pages/photos.html", "photos"),
    ("facilities.html", "pages/facilities.html", "facilities"),
    ("facilities-green-room.html", "pages/facilities-green-room.html", "facilities"),
    ("facilities-toilet.html", "pages/facilities-toilet.html", "facilities"),
    ("transportation.html", "pages/transportation.html", "transportation"),
    ("transportation-bus.html", "pages/transportation-bus.html", "transportation"),
    ("transportation-auto.html", "pages/transportation-auto.html", "transportation"),
    ("help.html", "pages/help.html", "help"),
]


def short_hash(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()[:10]


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    src_assets = SITE / "assets"
    out_assets = DIST / "assets"
    out_assets.mkdir(parents=True)
    manifest: dict[str, str] = {}
    for src in src_assets.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(src_assets)
        if rel.suffix in (".css", ".js"):
            h = short_hash(src)
            out_rel = rel.with_name(f"{rel.stem}.{h}{rel.suffix}")
        else:
            out_rel = rel
        out_path = out_assets / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out_path)
        manifest[str(rel).replace("\\", "/")] = "/assets/" + str(out_rel).replace("\\", "/")

    env = Environment(
        loader=FileSystemLoader(str(SITE / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    # BASE is prepended to every asset URL and every {{ base }} reference
    env.globals["asset"] = lambda name: BASE + manifest.get(name, "/assets/" + name)
    env.globals["version"] = "3.0.0"

    for tpl_name, out_name, nav in PAGES:
        tpl = env.get_template(tpl_name)
        html = tpl.render(active=nav, base=BASE)
        out_path = DIST / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")

    shutil.copy(SITE / "robots.txt", DIST / "robots.txt")
    print(f"Built {len(PAGES)} pages -> {DIST}  (base={BASE or '/':<12})")


if __name__ == "__main__":
    main()
