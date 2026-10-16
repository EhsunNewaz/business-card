#!/usr/bin/env python3
"""
IELTS Simon — IELTS Speaking post archiver (Wayback Machine).

The old blog ielts-simon.com published ~2,800 daily lessons from 2009 to
early 2020, and a couple of stragglers in 2021.  This script pulls the whole
*IELTS Speaking* track out of the Wayback Machine and stores it, per post, as

    scrape/simon-wayback/speaking-comments/<YYYY-MM>-<slug>.json

with the post title, the publish date, the comment count and **every comment
with its author and its exact timestamp**.

Two things are harvested per post:

* the *comment feed* — Typepad exposed `…/<post>/comments/atom.xml`, and
  Wayback archived it.  Each entry carries the author, `published`,
  `updated` and the comment body.
* the *post page* — used as a fallback when a post's feed was never archived
  (e.g. the 2021 posts) and as the source of the publish date + title.

Usage
-----
    pip install requests

    # 1. refresh the URL inventory from the CDX API
    python3 scrape/simon-wayback/fetch_speaking_archive.py --list-only

    # 2. fetch every post (feed first, post page as fallback)
    python3 scrape/simon-wayback/fetch_speaking_archive.py --all

    # only what is missing (resumable)
    python3 scrape/simon-wayback/fetch_speaking_archive.py --all --resume

    # only the newest N posts
    python3 scrape/simon-wayback/fetch_speaking_archive.py --all --limit 50

    # where are we?
    python3 scrape/simon-wayback/fetch_speaking_archive.py --status

Outputs
-------
    scrape/simon-wayback/raw-speaking-cdx.txt        URL inventory (CDX API)
    scrape/simon-wayback/speaking-comments/*.json     one file per post
    scrape/simon-wayback/speaking-coverage.txt        coverage report
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CDX_RAW = HERE / "raw-speaking-cdx.txt"
OUT_DIR = HERE / "speaking-comments"
COVERAGE = HERE / "speaking-coverage.txt"

CDX_URL = (
    "https://web.archive.org/cdx/search/cdx"
    "?url=ielts-simon.com/ielts-help-and-english-pr/*"
    "&output=text&fl=original&collapse=urlkey"
    "&filter=statuscode:200"
    "&filter=original:.*ielts-speaking-.*\\.html$"
    "&limit=6000"
)

ORIGIN = "https://www.ielts-simon.com/ielts-help-and-english-pr"
WAYBACK_PREFIX = "https://web.archive.org/web/2021id_"

ENTRY_RE = re.compile(
    r"([^\s]+) commented on '([^']*)'tag:typepad\.com,2003:(\S+?)"
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
    r"([^\s]*?)"
    r"(.*?)(?=(?:[^\s]+ commented on ')|$)",
    re.S,
)
TITLE_RE = re.compile(r"Comments on (.+?)TypePad", re.S)
POST_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")
TAG_RE = re.compile(r"<[^>]+>")

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def normalise_url(raw: str) -> str:
    """CDX rows -> 'ielts-simon.com/ielts-help-and-english-pr/YYYY/MM/slug.html'."""
    u = raw.strip()
    if not u.startswith("http"):
        return ""
    if "..." in u:  # CDX wildcard row, not a real path
        return ""
    u = u.split("://", 1)[1]
    u = u.replace(":80/", "/")
    u = re.sub(r"^www\.", "", u)
    return u


def read_inventory() -> list[dict]:
    """[{ym, slug, url, orig_path}] from raw-speaking-cdx.txt, deduped + sorted."""
    if not CDX_RAW.exists():
        sys.exit(f"missing {CDX_RAW} — run with --list-only first")
    seen: dict[str, dict] = {}
    for line in CDX_RAW.read_text(encoding="utf-8").splitlines():
        key = normalise_url(line)
        if not key:
            continue
        m = re.search(r"ielts-help-and-english-pr/(\d{4})/(\d{2})/(.+)\.html$", key)
        if not m:
            continue
        ym, slug = f"{m.group(1)}/{m.group(2)}", m.group(3)
        if slug in seen:
            continue
        seen[slug] = {
            "ym": ym,
            "slug": slug,
            "url": f"{ORIGIN}/{ym}/{slug}.html",
            "feed": f"{ORIGIN}/{ym}/{slug}/comments/atom.xml",
        }
    posts = sorted(seen.values(), key=lambda p: (p["ym"], p["slug"]))
    return posts


def out_path(post: dict) -> Path:
    return OUT_DIR / f"{post['ym'].replace('/', '-')}-{post['slug']}.json"


def http_get(url: str, tries: int = 3) -> str:
    import requests

    last = ""
    for attempt in range(tries):
        try:
            r = requests.get(url, timeout=45, headers={"User-Agent": "Mozilla/5.0 simon-research"})
            if r.status_code == 200:
                return r.text
            last = f"HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{last} for {url}")


def strip_html(text: str) -> str:
    import html as html_mod

    text = re.sub(r"<\s*p\s*/?>", "\n\n", text, flags=re.I)
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.I)
    text = TAG_RE.sub("", text)
    text = html_mod.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_feed(raw: str) -> tuple[str, list[dict]]:
    """-> (post_title, [comment dicts]) from an atom feed (xml or mangled text)."""
    title = ""
    m = TITLE_RE.search(raw)
    if m:
        title = strip_html(m.group(1)).strip()

    comments: list[dict] = []
    for em in ENTRY_RE.finditer(raw):
        author, ctitle, cid, published, updated, summary = em.groups()
        body = strip_html(summary)
        if not body:
            continue
        comments.append(
            {
                "id": cid,
                "author": author,
                "post_title": ctitle,
                "published": published,
                "updated": updated,
                "text": body,
            }
        )
    if not title and comments:
        title = comments[0]["post_title"]
    return title, comments


def parse_post_page(raw: str) -> dict:
    """Pull title / date / comments out of a rendered post page."""
    title = ""
    m = re.search(r"^#\s+(.+)$", raw, re.M)
    if m:
        title = m.group(1).strip()
    if not title:
        m = re.search(r"<title>(.+?)</title>", raw, re.S | re.I)
        if m:
            title = strip_html(m.group(1)).split(" - ")[0].strip()

    published = ""
    m = re.search(r"^##\s+([A-Z][a-z]+ \d{1,2}, \d{4})", raw, re.M)
    if m:
        try:
            published = date(int(m.group(1).split(", ")[1]), MONTHS.index(m.group(1).split()[0]) + 1,
                             int(m.group(1).split()[1])).isoformat()
        except (ValueError, IndexError):
            published = ""

    comments: list[dict] = []
    block = raw.split("### Comments", 1)
    if len(block) == 2:
        body = block[1]
        # each comment: text ... "Posted by:" NAME | [Month DD, YYYY at HH:MM](url)
        pattern = re.compile(
            r"(.*?)\s*Posted by:\s*(.+?)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)",
            re.S,
        )
        for cm in pattern.finditer(body):
            text = strip_html(cm.group(1))
            if not text:
                continue
            comments.append(
                {
                    "id": cm.group(4).split("#comment-")[-1],
                    "author": cm.group(2).strip(),
                    "post_title": title,
                    "published": cm.group(3).strip(),
                    "updated": cm.group(3).strip(),
                    "text": text,
                }
            )
    return {"title": title, "published": published, "comments": comments}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def cmd_list_only() -> None:
    print(f"GET {CDX_URL}")
    raw = http_get(CDX_URL)
    header = (
        "# IELTS Simon — IELTS Speaking post URL inventory (Wayback Machine CDX API)\n"
        "#\n"
        "# Source query:\n"
        "#   https://web.archive.org/cdx/search/cdx\n"
        "#     ?url=ielts-simon.com/ielts-help-and-english-pr/*\n"
        "#     &output=text&fl=original&collapse=urlkey\n"
        "#     &filter=statuscode:200\n"
        "#     &filter=original:.*ielts-speaking-.*\\.html$\n"
        "#     &limit=6000\n"
        "#\n"
        f"# {len(raw.splitlines())} raw rows — 2009-09 -> 2021-08.\n"
        "#\n"
        "# Regenerate with: python3 scrape/simon-wayback/fetch_speaking_archive.py --list-only\n"
        "#\n"
    )
    CDX_RAW.write_text(header + raw.strip() + "\n", encoding="utf-8")
    print(f"wrote {CDX_RAW.relative_to(REPO)} ({len(raw.splitlines())} rows)")


def cmd_fetch(args) -> None:
    posts = read_inventory()
    if args.newest_first:
        posts = sorted(posts, key=lambda p: (p["ym"], p["slug"]), reverse=True)
    if args.limit:
        posts = posts[: args.limit]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = skipped = failed = 0
    for i, post in enumerate(posts, 1):
        dest = out_path(post)
        if args.resume and dest.exists():
            skipped += 1
            continue
        record = {"ym": post["ym"], "slug": post["slug"], "url": post["url"],
                  "title": "", "published": "", "comments": [], "source": ""}
        try:
            raw = http_get(f"{WAYBACK_PREFIX}/{post['feed']}")
            title, comments = parse_feed(raw)
            if title:
                record["title"] = title
            record["comments"] = comments
            record["source"] = "atom-feed"
            if not comments:
                record["source"] = "atom-feed (empty)"
        except Exception as exc:  # noqa: BLE001
            record["source"] = f"feed-failed: {exc}"
        if not record["comments"] and record["source"] != "atom-feed":
            try:
                raw = http_get(f"{WAYBACK_PREFIX}/{post['url']}")
                page = parse_post_page(raw)
                record["title"] = record["title"] or page["title"]
                record["published"] = page["published"]
                record["comments"] = page["comments"]
                record["source"] = "post-page" if page["comments"] else "post-page (no comments)"
            except Exception as exc:  # noqa: BLE001
                record["source"] += f" | post-page-failed: {exc}"
                failed += 1
        if not record["title"] and record["comments"]:
            record["title"] = record["comments"][0]["post_title"]
        dest.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        done += 1
        print(f"[{i}/{len(posts)}] {post['ym']} {post['slug']} "
              f"-> {len(record['comments'])} comments ({record['source']})")
    write_coverage(posts)
    print(f"\ndone={done} skipped={skipped} failed={failed}")


def write_coverage(posts: list[dict] | None = None) -> None:
    posts = posts or read_inventory()
    total = len(posts)
    have = 0
    n_comments = 0
    years: dict[str, list[int]] = {}
    for post in posts:
        p = out_path(post)
        n = 0
        if p.exists():
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
                n = len(rec.get("comments", []))
                have += 1
                n_comments += n
            except (OSError, json.JSONDecodeError):
                pass
        y = post["ym"][:4]
        years.setdefault(y, [0, 0])
        years[y][0] += 1
        years[y][1] += n
    lines = [
        f"speaking posts in archive: {total}",
        f"posts with comment data:   {have} ({have * 100 // total if total else 0}%)",
        f"comments captured:         {n_comments}",
        "",
        "per year (posts / comments):",
    ]
    for y in sorted(years):
        lines.append(f"  {y}: {years[y][0]:4d} posts  {years[y][1]:5d} comments")
    COVERAGE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"coverage -> {COVERAGE.relative_to(REPO)}")


def cmd_status() -> None:
    write_coverage()
    print(COVERAGE.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-only", action="store_true", help="refresh raw-speaking-cdx.txt from the CDX API")
    ap.add_argument("--all", action="store_true", help="fetch every post in the inventory")
    ap.add_argument("--resume", action="store_true", help="skip posts that already have a json file")
    ap.add_argument("--limit", type=int, default=0, help="only fetch the first N posts")
    ap.add_argument("--newest-first", action="store_true", help="work backwards from the newest post")
    ap.add_argument("--status", action="store_true", help="print the coverage report")
    args = ap.parse_args()

    if args.list_only:
        cmd_list_only()
    if args.status or not (args.list_only or args.all):
        cmd_status()
    if args.all:
        cmd_fetch(args)


if __name__ == "__main__":
    main()
