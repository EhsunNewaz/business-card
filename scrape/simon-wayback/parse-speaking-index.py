#!/usr/bin/env python3
"""
Parse the captured monthly archive index pages into per-post body records.

The Typepad monthly index (`/{YYYY}/{MM}/index.html`) lists every post of that
month with its **full body**, its **publish date** and its **comment count**
(`Comments (N)`).  That makes it the densest body source in the archive: one
fetched page covers every speaking post of a month.

Input
    scrape/simon-wayback/speaking-index/<YYYY-MM>.txt

    A header block (written by the fetcher) followed by the page text exactly
    as the Wayback reader rendered it:

        # source: https://web.archive.org/web/20210917064830id_/https://...
        # captured: 2026-10-17
        ## August 30, 2021
        ### [IELTS Grammar / Vocabulary: correct the mistakes](http://...)
        <body>
        Posted by Simon in [IELTS Speaking](http://...) | [Permalink](http://...) | [Comments (0)](http://...#comments)

    The reader splits a page into chunks; the fetcher concatenates them in
    order, so the text is contiguous again.

Output
    scrape/simon-wayback/speaking-bodies/<YYYY-MM>-<slug>.txt

        # post: 2021-08 | ielts-speaking-part-1-which-method-is-best
        # title: IELTS Speaking Part 1: which method is best?
        # date: 2021-08-23
        # comments: 0
        # url: https://www.ielts-simon.com/.../ielts-speaking-part-1-which-method-is-best.html
        # source: https://web.archive.org/web/20210917064830id_/https://...
        # captured: 2026-10-17
        <post body, paragraphs separated by " / ">

Re-run after adding more index pages:
    python3 scrape/simon-wayback/parse-speaking-index.py
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX_DIR = HERE / "speaking-index"
BODY_DIR = HERE / "speaking-bodies"

# "## Wednesday, September 30, 2009"  /  "## August 30, 2021"
DATE_RE = re.compile(
    r"^##\s+(?:[A-Z][a-z]+day,\s*)?([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})\s*$"
)
# "## 2020-02-21" — the compact form the fetcher writes
ISO_DATE_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
# "### [Title](url)"  /  "### Title"
HEAD_RE = re.compile(r"^###\s+\[(.+?)\]\((\S+?)\)\s*$")
PLAIN_HEAD_RE = re.compile(r"^###\s+(.+?)\s*$")
URL_LINE_RE = re.compile(r"^#\s*url:\s*(\S+)\s*$")
COMMENTS_LINE_RE = re.compile(r"^#\s*comments:\s*(\d+)\s*$")
# "Posted by Simon in [Cat](..) | [Permalink](..) | [Comments (3)](..)"
POSTED_RE = re.compile(r"^Posted by .*?\[Permalink\]\((\S+?)\).*?\[Comments \((\d+)\)\]")
COMMENTS_RE = re.compile(r"\[Comments \((\d+)\)\]")

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
    "December": 12,
}


def parse_page(text: str) -> list[dict]:
    """-> [{date, title, slug, url, comments, body}] for every post on the page.

    Two input shapes are understood:

    * the raw Wayback reader rendering of a monthly index page —
      "## Wednesday, September 30, 2009" + "### [Title](url)" + a
      "Posted by ... [Comments (3)](...)" footer; and
    * the compact shape the fetcher writes —
      "## 2020-02-21" + "### Title" + "# url: ..." + "# comments: 3".
    """
    posts: list[dict] = []
    cur: dict | None = None
    body: list[str] = []

    def flush() -> None:
        if cur is None:
            return
        cur["body"] = "\n\n".join(b for b in body if b.strip()).strip()
        if cur["title"] and cur["body"]:
            posts.append(cur)

    for line in text.splitlines():
        m = ISO_DATE_RE.match(line)
        if m:
            flush()
            body = []
            cur = {"date": m.group(1), "title": "", "slug": "", "url": "",
                   "comments": 0, "body": ""}
            continue
        m = DATE_RE.match(line)
        if m:
            flush()
            body = []
            month = MONTHS.get(m.group(1))
            cur = {
                "date": f"{m.group(3)}-{month:02d}-{int(m.group(2)):02d}" if month else "",
                "title": "", "slug": "", "url": "", "comments": 0, "body": "",
            }
            continue
        if cur is None:
            continue
        m = URL_LINE_RE.match(line)
        if m:
            cur["url"] = m.group(1)
            cur["slug"] = cur["url"].rstrip("/").split("/")[-1].replace(".html", "")
            continue
        m = COMMENTS_LINE_RE.match(line)
        if m:
            cur["comments"] = int(m.group(1))
            continue
        m = HEAD_RE.match(line)
        if m and not cur["title"]:
            cur["title"] = m.group(1).strip()
            cur["url"] = m.group(2).strip()
            cur["slug"] = cur["url"].rstrip("/").split("/")[-1].replace(".html", "")
            continue
        if not cur["title"]:
            m = PLAIN_HEAD_RE.match(line)
            if m:
                cur["title"] = m.group(1).strip()
                continue
        m = POSTED_RE.match(line)
        if m:
            cur["url"] = m.group(1)
            cur["comments"] = int(m.group(2))
            cur["slug"] = cur["url"].rstrip("/").split("/")[-1].replace(".html", "")
            continue
        if cur["title"]:
            body.append(line.rstrip())
    flush()
    return posts


def main() -> None:
    BODY_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(INDEX_DIR.glob("*.txt"))
    total = 0
    speaking = 0
    for f in files:
        raw = f.read_text(encoding="utf-8")
        source = ""
        captured = ""
        lines: list[str] = []
        for ln in raw.splitlines():
            if ln.startswith("# source:"):
                source = ln.split(":", 1)[1].strip()
                continue
            if ln.startswith("# captured:"):
                captured = ln.split(":", 1)[1].strip()
                continue
            lines.append(ln)
        page = "\n".join(lines)
        posts = parse_page(page)
        total += len(posts)
        for p in posts:
            if "ielts-speaking" not in p["slug"]:
                continue
            speaking += 1
            out = BODY_DIR / f"{p['date'][:7]}-{p['slug']}.txt"
            head = [
                f"# post: {p['date'][:7]} | {p['slug']}",
                f"# title: {p['title']}",
                f"# date: {p['date']}",
                f"# comments: {p['comments']}",
                f"# url: {p['url']}",
                f"# source: {source}",
                f"# captured: {captured}",
            ]
            paras = [b.strip() for b in p["body"].split("\n\n") if b.strip()]
            out.write_text("\n".join(head) + "\n" + "\n\n".join(paras) + "\n", encoding="utf-8")
    print(f"index files: {len(files)} · posts parsed: {total} · speaking bodies: {speaking}")


if __name__ == "__main__":
    main()
