#!/usr/bin/env python3
"""
Build the categorized index of Simon's old blog posts from scrape/simon-wayback/raw-index.txt
(raw data = Wayback Machine CDX API, one slug per line, grouped under '# YEAR' / '## YYYY-MM' headers).

Output: master/07a-simon-oldblog-archive-index.md
Re-run after appending more years to raw-index.txt.
"""
import re
from collections import defaultdict
from datetime import date

RAW = "scrape/simon-wayback/raw-index.txt"
OUT = "master/07a-simon-oldblog-archive-index.md"

CATS = [
    ("IELTS Listening", "L"),
    ("IELTS Reading", "R"),
    ("IELTS Speaking", "S"),
    ("Writing Task 1 (Academic)", "W1"),
    ("Writing Task 2", "W2"),
    ("General Writing (GT Task 1)", "GT"),
    ("Vocabulary & Grammar", "GV"),
    ("Advice / Students' Questions", "ADV"),
    ("Blog news & announcements", "MISC"),
]
CODE2NAME = {c: n for n, c in CATS}

def classify(slug: str) -> str:
    s = slug
    if "general-writing" in s or "general-training" in s:
        return "GT"
    if "writing-task-1" in s:
        return "W1"
    if "writing-task-2" in s:
        return "W2"
    if "listening" in s or s.startswith("listen"):
        return "L"
    if "reading" in s:
        return "R"
    if "speaking" in s:
        return "S"
    if "grammar" in s or "vocabulary" in s or "collocation" in s:
        return "GV"
    if "advice" in s or "students-question" in s:
        return "ADV"
    if "writing" in s:  # generic writing-advice post (no task number)
        return "ADV"
    return "MISC"

def main():
    year, month = None, None
    posts = []  # (year, month, slug, category_code)
    seen = set()
    dupes = []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("# YEAR "):
                year = line.split()[-1]
            elif line.startswith("## "):
                month = line[3:]
            else:
                key = (month, line)
                if key in seen:
                    dupes.append(key)
                    continue
                seen.add(key)
                posts.append((year, month, line, classify(line)))

    by_cat = defaultdict(list)   # code -> [(month, slug)]
    by_year_cat = defaultdict(int)  # (year, code) -> count
    for y, m, slug, code in posts:
        by_cat[code].append((m, slug))
        by_year_cat[(y, code)] += 1

    years = sorted({y for y, _, _, _ in posts})
    total = len(posts)

    lines = []
    lines.append("---")
    lines.append('title: "IELTS Simon পুরনো ব্লগের আর্কাইভ ইনডেক্স — ক্যাটাগরি + তারিখসহ সব পোস্ট (2018–2019 সহযোগে)"')
    lines.append('slug: "ielts-simon-oldblog-archive-index"')
    lines.append("module: Reference / Archive")
    lines.append(f"generated: {date.today().isoformat()}")
    lines.append("---")
    lines.append("")
    lines.append("# IELTS Simon পুরনো ব্লগের আর্কাইভ ইনডেক্স (ক্যাটাগরি + মাসসহ)")
    lines.append("")
    lines.append("> **সোর্স:** Wayback Machine CDX API — প্রতিটা পোস্টের archived URL থেকে নেওয়া। র ফাইল: `scrape/simon-wayback/raw-index.txt` (slug + মাস)। জেনারেটর: `scrape/simon-wayback/build-index.py`।")
    lines.append(">")
    lines.append("> **লিংক:** নিচের প্রতিটা slug-ই ক্লিকেবল — ক্লিক করলেই Wayback Machine-এ ঐ পোস্টটা খোলে।")
    lines.append("> (ফরম্যাট: `https://web.archive.org/web/2024/https://www.ielts-simon.com/ielts-help-and-english-pr/YYYY/MM/SLUG.html`)।")
    lines.append(">")
    lines.append(f"> **কভারেজ:** এই ভার্সনে {', '.join(years)} — মোট **{total}টা পোস্ট**। বাকি বছর (2009–2017, 2020–2021) পরের ব্যাচে যোগ হবে (archive.org সাময়িক অফলাইন ছিল)।")
    lines.append("")
    lines.append("## ক্যাটাগরি-বাই-ইয়ার কাউন্ট")
    lines.append("")
    header = "| ক্যাটাগরি | " + " | ".join(years) + " | মোট |"
    lines.append(header)
    lines.append("|" + "---|" * (len(years) + 2))
    for name, code in CATS:
        row = [str(by_year_cat.get((y, code), 0)) for y in years]
        tot = sum(int(r) for r in row)
        lines.append(f"| {name} | " + " | ".join(row) + f" | **{tot}** |")
    lines.append("| **মোট** | " + " | ".join(f"**{sum(1 for p in posts if p[0]==y)}**" for y in years) + f" | **{total}** |")
    lines.append("")

    for name, code in CATS:
        items = by_cat.get(code, [])
        lines.append(f"## {name} ({len(items)})")
        lines.append("")
        cur_month = None
        for m, slug in items:
            if m != cur_month:
                lines.append(f"**{m}**")
                cur_month = m
            lines.append(f"- [{slug}](https://web.archive.org/web/2024/https://www.ielts-simon.com/ielts-help-and-english-pr/{m}/{slug}.html)")
        lines.append("")

    if dupes:
        lines.append("## ডুপ্লিকেট (একই মাসে একই slug দুইবার — র ফাইলে একবারই রাখা হয়েছে)")
        lines.append("")
        for m, slug in dupes:
            lines.append(f"- {m} · {slug}")
        lines.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"posts: {total}")
    for name, code in CATS:
        print(f"  {code:4} {name}: {len(by_cat.get(code, []))}")
    print(f"years: {years}")
    if dupes:
        print(f"dupes skipped: {len(dupes)}")

if __name__ == "__main__":
    main()
