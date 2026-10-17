#!/usr/bin/env python3
"""
Build the IELTS Speaking archive corpus + master doc from the raw Wayback dumps.

Inputs
------
    scrape/simon-wayback/raw-speaking-cdx.txt   URL inventory (CDX API)  -> every post
    scrape/simon-wayback/speaking-feeds/*.txt   Typepad comment feeds   -> comments
    scrape/simon-wayback/speaking-pages/*.txt   fallback post pages

Outputs
-------
    scrape/simon-wayback/speaking-comments/<YYYY-MM>-<slug>.json  structured record
    scrape/simon-wayback/speaking-corpus/<YYYY-MM-DD>_<slug>.md   readable corpus
    master/09-simon-speaking-posts-archive.md                     the master doc

Re-run after adding more feeds:
    python3 scrape/simon-wayback/build-speaking-doc.py
"""
from __future__ import annotations

import html as html_mod
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CDX_RAW = HERE / "raw-speaking-cdx.txt"
FEED_DIR = HERE / "speaking-feeds"
PAGE_DIR = HERE / "speaking-pages"
BODY_DIR = HERE / "speaking-bodies"
JSON_DIR = HERE / "speaking-comments"
CORPUS_DIR = HERE / "speaking-corpus"
COVERAGE = HERE / "speaking-coverage.txt"
OUT = REPO / "master" / "09-simon-speaking-posts-archive.md"

ORIGIN = "https://www.ielts-simon.com/ielts-help-and-english-pr"

ENTRY_RE = re.compile(
    r"([^\s]+) commented on '([^']*)'tag:typepad\.com,2003:(\S+?)"
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
    r"([^\s]*?)"
    r"(.*?)(?=(?:[^\s]+ commented on ')|$)",
    re.S,
)
TITLE_RE = re.compile(r"Comments on (.+?)TypePad", re.S)
TAG_RE = re.compile(r"<[^>]+>")
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------
def strip_html(text: str) -> str:
    text = re.sub(r"<\s*p\s*/?>", "\n\n", text, flags=re.I)
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.I)
    text = TAG_RE.sub("", text)
    text = html_mod.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_inventory() -> list[dict]:
    # NB: Simon reused slugs across months (e.g. ielts-speaking-correct-the-mistakes
    # ran every month), so a post is identified by (year-month, slug) — not slug.
    seen: dict[tuple[str, str], dict] = {}
    for line in CDX_RAW.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("http") or "..." in line:
            continue
        path = line.split("://", 1)[1].replace(":80/", "/")
        path = re.sub(r"^www\.", "", path)
        m = re.search(r"ielts-help-and-english-pr/(\d{4})/(\d{2})/(.+)\.html$", path)
        if not m:
            continue
        ym, slug = f"{m.group(1)}-{m.group(2)}", m.group(3)
        seen.setdefault((ym, slug), {
            "ym": ym,
            "ym_slash": f"{m.group(1)}/{m.group(2)}",
            "slug": slug,
            "url": f"{ORIGIN}/{m.group(1)}/{m.group(2)}/{slug}.html",
            "feed": f"{ORIGIN}/{m.group(1)}/{m.group(2)}/{slug}/comments/atom.xml",
        })
    return sorted(seen.values(), key=lambda p: (p["ym"], p["slug"]))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _split_author(tail: str) -> tuple[str, str]:
    """
    A Typepad feed entry flattens to:

        <author> commented on '<title>' <post-uri> <published> <updated>
        <author> <summary-preview> <p>full comment body</p>

    The preview is a truncation of the body, so the author is whatever precedes
    the longest prefix of the body.  Recovered by walking candidate split
    points and matching the preview against the body.
    """
    pidx = tail.find("<p>")
    if pidx < 0:
        return tail.strip(), tail
    before = tail[:pidx]
    body = tail[pidx:]
    # the entry's body is every <p> block up to the last </p> in this segment
    last = body.rfind("</p>")
    inner = body[3:last + 4] if last >= 0 else body[3:]
    norm_inner = _norm(html_mod.unescape(re.sub(r"<br\s*/?>", " ", inner)))
    for k in range(1, len(before) + 1):
        cand = _norm(html_mod.unescape(before[k:])).rstrip(".").strip()
        if len(cand) < 4:
            break
        if norm_inner.startswith(cand[: min(len(cand), 80)]):
            return _clean_author(before[:k]), inner
    return _clean_author(before), inner


def _clean_author(author: str) -> str:
    """Strip any URL that leaked in from the comment body."""
    author = re.split(r"https?://", author)[0]
    return author.strip(" ,.:;-")


def parse_feed(raw: str) -> tuple[str, list[dict]]:
    """
    A Typepad comment feed flattens to one long line per feed:

        <Author> commented on '<title>' <uri> <published> <updated> <Author>
        <summary-preview><p>body</p> <next Author> commented on '<title>' ...

    The author is recovered from the *end of the previous segment* (it is the
    text after the previous comment's last </p>), which is exact; the body comes
    from the <p> blocks, falling back to the summary preview when the reader
    mangled them.
    """
    title = ""
    m = TITLE_RE.search(raw)
    if m:
        title = strip_html(m.group(1)).strip()

    segs = raw.split(" commented on '")
    comments = []
    for i, seg in enumerate(segs[1:], start=1):
        prev = segs[i - 1]
        # author of this entry = the trailing name of the previous segment
        m = re.search(r"</p>([^<>]*)$", prev)
        author = m.group(1).strip() if m else prev.rsplit("/", 1)[-1].strip()
        author = re.split(r"https?://", author)[0].strip(" ,.:;-")

        ctitle, _, rest = seg.partition("'")
        m = re.match(
            r"tag:typepad\.com,2003:(\S+?)"
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)(.*)$",
            rest, re.S,
        )
        if not m:
            continue
        cid, published, updated, tail = m.groups()

        # body from the <p> blocks of this entry
        body_src = tail
        p = body_src.find("<p>")
        inner = ""
        if p >= 0:
            chunk = body_src[p:]
            last = chunk.rfind("</p>")
            inner = chunk[3:last + 4] if last >= 0 else chunk[3:]
        body = strip_html(inner)

        # summary preview = the text before the first <p>, minus the author name
        preview = ""
        if p >= 0:
            before = body_src[:p]
            if author and before.startswith(author):
                before = before[len(author):]
            preview = strip_html(before).strip()
        if len(preview) > len(body):
            body = preview

        if not body:
            continue
        comments.append({
            "id": cid,
            "author": author,
            "post_title": ctitle,
            "published": published,
            "updated": updated,
            "text": body,
        })
    if not title and comments:
        title = comments[0]["post_title"]
    return title, comments


def parse_compact_feed(raw: str) -> tuple[str, list[dict]]:
    """
    Compact capture format used for the bulk sweep (one line per comment):

        # post: 2019-10 | ielts-speaking-part-2-describe-a-book
        # title: IELTS Speaking Part 2: describe a book
        # source: https://web.archive.org/web/.../comments/atom.xml
        published :: updated :: author :: text

    Paragraph breaks inside a comment are stored as " / ".
    """
    title = ""
    comments = []
    for line in raw.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("# title:"):
            title = line.split(":", 1)[1].strip()
            continue
        if line.startswith("#"):
            continue
        parts = line.split(" :: ", 3)
        if len(parts) == 4:
            published, updated, author, text = parts
        elif len(parts) == 3:
            # older captures used "author : text" instead of "author :: text"
            published, updated, rest = parts
            m = re.match(r"([^:]{1,80}?)\s:\s(.*)$", rest, re.S)
            if not m:
                continue
            author, text = m.group(1), m.group(2)
        else:
            continue
        text = text.replace(" / ", "\n\n").strip()
        if not text:
            continue
        comments.append({
            "id": "",
            "author": author.strip(),
            "post_title": title,
            "published": published.strip(),
            "updated": updated.strip(),
            "text": text,
        })
    return title, comments


def parse_body_capture(raw: str) -> dict:
    """Parse a `speaking-bodies/<YYYY-MM>-<slug>.txt` capture.

        # post: 2020-02 | ielts-speaking-part-2-using-the-prompts
        # title: IELTS Speaking Part 2: using the prompts
        # date: 2020-02-21
        # comments: 2
        # url: https://ielts-simon.com/...
        # source: https://web.archive.org/web/.../index.html
        # captured: 2026-10-17
        <post body — paragraphs separated by " / ">
    """
    meta: dict[str, str] = {}
    body_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("# "):
            key, _, val = line[2:].partition(":")
            meta[key.strip()] = val.strip()
            continue
        body_lines.append(line)
    text = "\n".join(body_lines).strip()
    # paragraphs are separated by blank lines inside the capture file
    paras = []
    for block in text.split("\n\n"):
        joined = "\n".join(x.rstrip() for x in block.split("\n") if x.strip())
        if joined:
            paras.append(joined)
    ts = ""
    m = re.search(r"web\.archive\.org/web/(\d{14})", meta.get("source", ""))
    if m:
        ts = m.group(1)
    return {
        "title": meta.get("title", ""),
        "date": meta.get("date", ""),
        "comments": int(meta.get("comments", "0") or 0),
        "url": meta.get("url", ""),
        "source": meta.get("source", ""),
        "ts": ts,
        "body": "\n\n".join(paras),
    }


def parse_page(raw: str) -> tuple[str, str, list[dict]]:
    title = ""
    m = re.search(r"^###\s+(.+)$", raw, re.M)
    if m:
        title = m.group(1).strip()
    published = ""
    m = re.search(r"^##\s+([A-Z][a-z]+ \d{1,2}, \d{4})", raw, re.M)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%B %d, %Y").date()
            published = dt.isoformat()
        except ValueError:
            published = ""
    comments = []
    block = raw.split("### Comments", 1)
    if len(block) == 2:
        for cm in re.finditer(r"(.*?)\s*Posted by:\s*(.+?)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)",
                              block[1], re.S):
            body = strip_html(cm.group(1))
            if not body:
                continue
            comments.append({
                "id": cm.group(4).split("#comment-")[-1],
                "author": cm.group(2).strip(),
                "post_title": title,
                "published": cm.group(3).strip(),
                "updated": cm.group(3).strip(),
                "text": body,
            })
    return title, published, comments


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def main() -> None:
    posts = read_inventory()
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    written: set[str] = set()
    for post in posts:
        stem = f"{post['ym']}-{post['slug']}"
        rec = {
            "ym": post["ym"],
            "slug": post["slug"],
            "url": post["url"],
            "wayback": f"https://web.archive.org/web/2021/{post['url']}",
            "title": "",
            "published": "",
            "comments": [],
            "source": "index-only",
            "body": "",
            "body_source": "",
            "index_comments": 0,
        }
        feed = FEED_DIR / f"{stem}.txt"
        page = PAGE_DIR / f"{stem}.txt"
        body_file = BODY_DIR / f"{stem}.txt"
        if feed.exists():
            raw = feed.read_text(encoding="utf-8")
            if raw.lstrip().startswith("# post:"):
                title, comments = parse_compact_feed(raw)
                rec["source"] = "atom-feed (compact)"
            else:
                title, comments = parse_feed(raw)
                rec["source"] = "atom-feed"
            rec["title"] = title
            rec["comments"] = comments
            if not comments and "no comment entries" in raw:
                rec["source"] = "atom-feed (no comments)"
        elif page.exists():
            title, published, comments = parse_page(page.read_text(encoding="utf-8"))
            rec["title"] = title
            rec["published"] = published
            rec["comments"] = comments
            rec["source"] = "post-page"
        if not rec["title"] and rec["comments"]:
            rec["title"] = rec["comments"][0]["post_title"]
        # post body (from the monthly index pages)
        if body_file.exists():
            b = parse_body_capture(body_file.read_text(encoding="utf-8"))
            rec["body"] = b["body"]
            rec["body_source"] = b["source"]
            rec["body_ts"] = b["ts"]
            rec["index_comments"] = b["comments"]
            if b["date"]:
                rec["published"] = b["date"]
            if not rec["title"]:
                rec["title"] = b["title"]
            if rec["source"] == "index-only":
                rec["source"] = "month-index"
        # json
        (JSON_DIR / f"{stem}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        # readable corpus — advice-corpus shape: content first, comments underneath
        if rec["comments"] or rec.get("body"):
            name = corpus_name(post, rec)
            write_corpus(CORPUS_DIR / name, post, rec)
            written.add(name)
        records.append(rec)

    # drop stale corpus files from earlier runs
    for old in CORPUS_DIR.glob("*.md"):
        if old.name not in written:
            old.unlink()

    write_coverage(records)
    write_index_tsv(records)
    write_master(records)


def write_index_tsv(records: list[dict]) -> None:
    """Machine readable index: one row per speaking post."""
    rows = ["ym\tslug\ttitle\tcomments\tsimon_replies\tstatus\twayback"]
    for r in records:
        replies = sum(1 for c in r["comments"]
                      if c["author"].strip().lower() in ("simon", "sjm", "martin"))
        status = r["source"] if r["comments"] else (
            "feed-archived-empty" if "no comments" in r["source"] else "no-comment-data")
        rows.append("\t".join([
            r["ym"], r["slug"], (r["title"] or "").replace("\t", " "),
            str(len(r["comments"])), str(replies), status, r["wayback"],
        ]))
    (HERE / "speaking-index.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def corpus_name(post: dict, rec: dict) -> str:
    """Corpus file name: `YYYY-MM-DD_<slug>_<N>c.md` (same shape as advice-corpus)."""
    datepart = rec["published"] if len(rec["published"]) == 10 else post["ym"]
    return f"{datepart}_{post['slug']}_{len(rec['comments'])}c.md"


def write_corpus(path: Path, post: dict, rec: dict) -> None:
    """Write one corpus file: the post's own content, then its comments.

    Mirrors `advice-corpus/` exactly — a title heading, a metadata line, a
    `## Content` section with the post body, and a `## Comments (N)` section
    listing every comment with its author and timestamp.
    """
    title = rec["title"] or post["slug"]
    n = len(rec["comments"])
    published = rec["published"] or post["ym"]
    # archive link for the post itself (not the monthly index page)
    ts = rec.get("body_ts") or ""
    if ts:
        wayback = f"https://web.archive.org/web/{ts}id_/{post['url']}"
    else:
        wayback = f"https://web.archive.org/web/2021/{post['url']}"
    L: list[str] = []
    L.append(f"# {title}")
    L.append("")
    L.append(f"- **Date:** {published} | **আর্কাইভ লিংক:** "
             f"[{post['ym_slash']}/{post['slug']}.html]({wayback}) | "
             f"**Comments:** {n}")
    L.append("")
    L.append("## Content")
    L.append("")
    if rec.get("body"):
        L.append(rec["body"])
    else:
        L.append("*(এই পোস্টের বডি এখনো ধরা পড়েনি — মাস-ইনডেক্স ফেচ করা বাকি)*")
    L.append("")
    L.append(f"## Comments ({n})")
    L.append("")
    for i, c in enumerate(rec["comments"], 1):
        pub = (c["published"] or "")[:10]
        stamp = pub
        upd = (c["updated"] or "")[:10]
        if upd and upd != pub:
            stamp = f"{pub} (এডিট {upd})"
        text = c["text"].replace("\n\n", " ").replace("\n", " ").strip()
        L.append(f'{i}. **{c["author"]}** ({stamp}): {text}')
    L.append("")
    path.write_text("\n".join(L), encoding="utf-8")


def write_coverage(records: list[dict]) -> None:
    total = len(records)
    with_comments = sum(1 for r in records if r["comments"])
    n_comments = sum(len(r["comments"]) for r in records)
    by_year: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in records:
        y = r["ym"][:4]
        by_year[y][0] += 1
        by_year[y][1] += len(r["comments"])
    lines = [
        f"speaking posts in archive: {total}",
        f"posts with comment data:   {with_comments} "
        f"({with_comments * 100 // total if total else 0}%)",
        f"comments captured:         {n_comments}",
        "",
        "per year (posts / comments captured):",
    ]
    for y in sorted(by_year):
        lines.append(f"  {y}: {by_year[y][0]:4d} posts  {by_year[y][1]:5d} comments")
    COVERAGE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_master(records: list[dict]) -> None:
    total = len(records)
    with_comments = sum(1 for r in records if r["comments"])
    with_body = sum(1 for r in records if r.get("body"))
    n_comments = sum(len(r["comments"]) for r in records)
    years = sorted({r["ym"][:4] for r in records})

    all_comments = [c for r in records for c in r["comments"]]
    by_author = Counter(c["author"] for c in all_comments)
    simon_replies = sum(1 for c in all_comments if c["author"].lower().startswith("simon"))
    months = Counter()
    for c in all_comments:
        try:
            months[c["published"][:7]] += 1
        except (IndexError, TypeError):
            pass

    L: list[str] = []
    L.append("---")
    L.append('title: "IELTS Simon-এর পুরনো ব্লগ — IELTS Speaking পোস্ট আর্কাইভ (কমেন্ট ও টাইমস্ট্যাম্প সহ, 2009–2021)"')
    L.append('slug: "ielts-simon-speaking-posts-archive"')
    L.append('meta_title: "IELTS Simon IELTS Speaking Blog Archive — All Posts with Comments (2009–2021)"')
    L.append('meta_description: "ielts-simon.com-এর পুরনো ব্লগের প্রতিটি IELTS Speaking পোস্ট — Wayback Machine থেকে সংগৃহীত, কমেন্ট ও তারিখসহ। সাইমনের নিজের উত্তর, স্টুডেন্টের প্রশ্ন ও IELTS ভাষা-সংশ্লেষণের জীবন্ত সম্প্রদায়।"')
    L.append('keywords: ["ielts simon speaking archive", "ielts speaking comments", "ielts speaking blog", "ielts simon wayback", "ielts speaking student questions"]')
    L.append('module: "Reference / Archive"')
    L.append(f"generated: {date.today().isoformat()}")
    L.append("---")
    L.append("")
    L.append("# IELTS Simon-এর পুরনো ব্লগ — IELTS Speaking পোস্ট আর্কাইভ")
    L.append("")
    L.append("> **সোর্স:** Wayback Machine-এ আর্কাইভ করা ielts-simon.com-এর *IELTS Speaking* ক্যাটাগরি।")
    L.append("> **ডেটা ফাইল:** `scrape/simon-wayback/raw-speaking-cdx.txt` (পোস্টের URL তালিকা, CDX API) ·")
    L.append("> `scrape/simon-wayback/speaking-feeds/` (কমেন্ট ফিড) · `scrape/simon-wayback/speaking-corpus/` (পূর্ণ কনটেন্ট+কমেন্ট) ·")
    L.append("> স্ক্র্যাপার: `scrape/simon-wayback/fetch_speaking_archive.py` · জেনারেটর: `scrape/simon-wayback/build-speaking-doc.py`")
    L.append(">")
    L.append("> **কেন এই ডক:** সাইমনের দৈনিক ব্লগ ২০০৯–২০২০ পর্যন্ত চলেছিল, আর ২০২১-এ আরও কয়েকটি পোস্ট এসেছিল।")
    L.append("> মূল সাইট ২০২৫ সেপ্টেম্বরে বন্ধ হয়ে গেছে, কিন্তু Wayback Machine-এ সব আছে — **কমেন্টসহ**।")
    L.append("> এই ডকে প্রতিটি পোস্টের লিংক, তারিখ ও কমেন্ট-কাউন্ট আছে; গভীর কর্পাসে পোস্টের পূর্ণ কনটেন্ট +")
    L.append("> **প্রতিটি কমেন্টের লেখক ও টাইমস্ট্যাম্প** সেভ করা আছে।")
    L.append("")
    L.append("## এক নজরে")
    L.append("")
    L.append("| পরিসংখ্যান | সংখ্যা |")
    L.append("|---|---|")
    L.append(f"| আর্কাইভে থাকা মোট IELTS Speaking পোস্ট | **{total}** |")
    L.append(f"| কমেন্ট ডেটাসহ পোস্ট | {with_comments} |")
    L.append(f"| পূর্ণ কনটেন্ট (বডি) সংগৃহীত পোস্ট | {with_body} |")
    L.append(f"| সংগৃহীত মোট কমেন্ট | **{n_comments}** |")
    L.append(f"| সাইমনের নিজের উত্তর | {simon_replies} |")
    L.append(f"| সময়কাল | {years[0]} → {years[-1]} |")
    L.append("")

    # year table
    L.append("## বছরভিত্তিক কভারেজ")
    L.append("")
    L.append("| বছর | পোস্ট | কমেন্ট ডেটাসহ পোস্ট | সংগৃহীত কমেন্ট | পূর্ণ কনটেন্ট সংগৃহীত পোস্ট |")
    L.append("|---|---|---|---|---|")
    for y in years:
        yr = [r for r in records if r["ym"].startswith(y)]
        wc = sum(1 for r in yr if r["comments"])
        nc = sum(len(r["comments"]) for r in yr)
        wb = sum(1 for r in yr if r.get("body"))
        L.append(f"| {y} | {len(yr)} | {wc} | {nc} | {wb} |")
    L.append("")

    # top engagement
    ranked = sorted((r for r in records if r["comments"]), key=lambda r: -len(r["comments"]))[:25]
    L.append("## সবচেয়ে বেশি আলোচিত ২৫টি পোস্ট (Engagement)")
    L.append("")
    L.append("| # | কমেন্ট | তারিখ | টাইটেল |")
    L.append("|---|---|---|---|")
    for i, r in enumerate(ranked, 1):
        title = r["title"] or r["slug"]
        L.append(f'| {i} | **{len(r["comments"])}** | {r["ym"]} | [{title}]({r["wayback"]}) |')
    L.append("")

    # top commenters
    L.append("## সবচেয়ে সক্রিয় কমেন্টকারীরা")
    L.append("")
    L.append("| কমেন্ট | নাম |")
    L.append("|---|---|")
    for name, n in by_author.most_common(20):
        L.append(f"| {n} | {name} |")
    L.append("")

    # engagement timeline
    L.append("## কমেন্ট-অ্যাক্টিভিটি টাইমলাইন (মাস অনুযায়ী)")
    L.append("")
    L.append("এটা দেখায় কোন সময় সাইমনের ব্লগ সবচেয়ে বেশি কমেন্ট পেয়েছিল —")
    L.append("একই সাথে ছাত্রদের কোন ধরনের প্রশ্ন সবচেয়ে বেশি এসেছে।")
    L.append("")
    L.append("| মাস | কমেন্ট |")
    L.append("|---|---|")
    for m in sorted(months):
        L.append(f"| {m} | {months[m]} |")
    L.append("")

    # full index
    L.append("---")
    L.append("")
    L.append("## সম্পূর্ণ পোস্ট ইনডেক্স (বছর অনুযায়ী)")
    L.append("")
    cur_year = None
    for r in records:
        y = r["ym"][:4]
        if y != cur_year:
            L.append("")
            L.append(f"### {y}")
            L.append("")
            L.append("| তারিখ | টাইটেল | কমেন্ট | কর্পাস |")
            L.append("|---|---|---|---|")
            cur_year = y
        title = r["title"] or r["slug"]
        n = len(r["comments"])
        star = " ★" if r["comments"] else ""
        cname = corpus_name({"slug": r["slug"], "ym": r["ym"]}, r)
        corpus = (f"[{cname}](../scrape/simon-wayback/speaking-corpus/{cname})"
                  if (r["comments"] or r.get("body")) else "—")
        L.append(f'| {r["ym"]} | [{title}]({r["wayback"]}){star} | {n}{"*" if n else ""} | {corpus} |')
    L.append("")
    L.append("★ = পূর্ণ কনটেন্ট + প্রতিটি কমেন্ট (লেখক ও টাইমস্ট্যাম্প সহ) কর্পাস ফোল্ডারে সেভ করা আছে।")
    L.append("")

    L.append("---")
    L.append("")
    L.append("## কমেন্ট থেকে কী বের হয় (রিসার্চ নোট)")
    L.append("")
    L.append("1. **সাইমন নিজেই উত্তর দেন** — ইংরেজিতে, ছাত্রের ভাষা-সংশ্লেষণ সরাসরি শুদ্ধ করে দেন।")
    L.append("   এটাই এই আর্কাইভের সবচেয়ে মূল্যবান অংশ: **একজন পরীক্ষক যেভাবে একজন শিক্ষকের মতো বলেন**।")
    L.append("2. **ছাত্ররা বাংলাদেশি ও ভারতীয়** — band score, retake, visa, চাকরির জন্য IELTS — এসব প্রশ্নের")
    L.append("   উত্তর সবচেয়ে বেশি। এটা আমাদের বাংলা অডিয়েন্সের জন্য সরাসরি ব্যবহারযোগ্য কনটেন্ট।")
    L.append("3. **আত্মসমালোচনার ভাষা** — 'I got band X, my weak area was Y' — এগুলো থেকে বাংলা ব্লগের")
    L.append("   কেস-স্টাডি সরাসরি তৈরি করা যায়।")
    L.append("4. **সিলেবাসের ফাঁকগুলো চোখে পড়ে** — ২০১৩–২০১৬-এ লেখক-ভিত্তিক vocabulary, collocation,")
    L.append("   'less common phrases' — এগুলো আমাদের master-০২-এর ভোকাবুলারি ব্যাংকে যাওয়া উচিত।")
    L.append("5. **সময়রেখা দেখায় সাইমনের teaching-ফোকাস বদলেছে** — ২০১৩-এ 'vocabulary + content' ছিল,")
    L.append("   ২০১৮-২০২০-এ 'simplify / fluent part 1 / answer-explain-example' — এই বদলের ধারা লেখা।")
    L.append("")
    L.append("## কীভাবে ব্যবহার করবেন")
    L.append("")
    L.append("- **বাংলা ব্লগের উৎস:** যেকোনো কমেন্ট থেকে একটি কেস-স্টাডি বানানো যায় —")
    L.append("  \"ছাত্র বলেছে এই ভুলটা করেছে, সাইমন এভাবে ঠিক করে দিয়েছেন\"।")
    L.append("- **স্টাডেন্ট ফোরামের ভিত্তি:** `speaking-corpus/`-এর ফাইলগুলো দেখে ছাত্রদের জন্য")
    L.append("  \"এই ধরনের প্রশ্ন করতে পারবে\" — সেটা প্রশ্ন ব্যাংক বানানোর পরের ধাপ।")
    L.append("- **মডেল উত্তরের সত্য উৎস:** সাইমনের নিজের উত্তরগুলো band-descriptor-based, তাই")
    L.append("  master-০২-এর মডেল উত্তর যাচাই করার সোর্স হিসেবে চলে।")
    L.append("")
    L.append("## সীমাবদ্ধতা ও সততা")
    L.append("")
    L.append("- পোস্টের URL তালিকা CDX API থেকে পাওয়া, যেখানে slug-এ `ielts-speaking` আছে।")
    L.append("  যেসব পোস্ট সাইমন Speaking ক্যাটাগরিতে দিয়েছিলেন কিন্তু slug-এ `ielts-speaking` নেই")
    L.append("  (যেমন `ielts-advice-…`, `ielts-vocabulary-…`), সেগুলো এই তালিকায় নেই।")
    L.append("- কমেন্ট ফিড না থাকা পোস্টগুলোতে (যেমন ২০২১-এর কয়েকটি) শুধু পোস্ট পেজ থেকে তথ্য নেওয়া হয়েছে।")
    L.append("- কমেন্টের লেখকের নামই প্রকাশিত; ইমেইল বা পরিচয় কিছুই সংগ্রহ করা হয়নি।")
    L.append("- কমেন্টে ছাত্রদের ব্যক্তিগত তথ্য (স্কোর, দেশ, নাম) থাকে — প্রকাশের আগে লেখক প্রসঙ্গে যাচাই করা উচিত।")
    L.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    print(f"  posts: {total} · with comments: {with_comments} · comments: {n_comments} · simon replies: {simon_replies}")


if __name__ == "__main__":
    main()
