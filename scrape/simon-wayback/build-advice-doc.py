#!/usr/bin/env python3
"""
Build master/07b-simon-advice-engagement.md from scrape/simon-wayback/advice-metrics.tsv
(date, ym, slug, title, comments). Re-run after appending more rows / corpus files.
"""
import os
import re
from datetime import date

TSV = "scrape/simon-wayback/advice-metrics.tsv"
COV = "scrape/simon-wayback/advice-coverage.txt"
CORPUS_DIR = "scrape/simon-wayback/advice-corpus"
OUT = "master/07b-simon-advice-engagement.md"

def main():
    rows = []
    with open(TSV, encoding="utf-8") as f:
        for line in f:
            if line.startswith("date\t") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 5:
                continue
            d, ym, slug, title, c = parts
            rows.append({"date": d, "ym": ym, "slug": slug, "title": title, "comments": int(c)})

    coverage = ""
    if os.path.exists(COV):
        coverage = open(COV, encoding="utf-8").read().strip()

    corpus_files = sorted(os.listdir(CORPUS_DIR)) if os.path.isdir(CORPUS_DIR) else []
    corpus_slugs = {f.split("_", 1)[1].rsplit("_", 1)[0] for f in corpus_files if f.endswith(".md")}

    def wb(ym: str, slug: str) -> str:
        return f"https://web.archive.org/web/2024/https://www.ielts-simon.com/ielts-help-and-english-pr/{ym}/{slug}.html"

    n = len(rows)
    total_c = sum(r["comments"] for r in rows)
    avg = total_c / n if n else 0
    zero = sum(1 for r in rows if r["comments"] == 0)
    top = sorted(rows, key=lambda r: -r["comments"])[:20]

    L = []
    L.append("---")
    L.append('title: "IELTS Simon-এর Advice পোস্টগুলো — কমেন্ট-কাউন্ট (Engagement) মেট্রিক টেবিল"')
    L.append('slug: "ielts-simon-advice-posts-engagement-metric"')
    L.append("module: Reference / Archive")
    L.append(f"generated: {date.today().isoformat()}")
    L.append("---")
    L.append("")
    L.append("# Simon-এর Advice পোস্ট — Engagement মেট্রিক (কমেন্ট সংখ্যা)")
    L.append("")
    L.append("> **সোর্স:** Wayback Machine-এ আর্কাইভ করা ielts-simon.com-এর \"Questions / Advice\" ক্যাটাগরি লিস্টিং পেইজ")
    L.append("> (প্রতিটা পোস্টের তারিখ + `Comments (N)` কাউন্ট ওখানে দেখা যায়)।")
    L.append("> **ডেটা ফাইল:** `scrape/simon-wayback/advice-metrics.tsv` · জেনারেটর: `scrape/simon-wayback/build-advice-doc.py`")
    L.append("> **লিংক:** নিচের প্রতিটা টাইটেল ক্লিক করলেই Wayback Machine-এ ঐ পোস্টটা খোলে")
    L.append("> (ফরম্যাট: `https://web.archive.org/web/2024/https://www.ielts-simon.com/ielts-help-and-english-pr/{ym}/{slug}.html`)।")
    L.append("> **গভীর কর্পাস (কনটেন্ট+কমেন্ট ফুল):** `scrape/simon-wayback/advice-corpus/` — এখন পর্যন্ত টপ পোস্টগুলো ঢুকছে।")
    L.append("")
    if coverage:
        L.append(f"> **কভারেজ স্ট্যাটাস:** {coverage}")
        L.append("")
    L.append("## এক নজরে")
    L.append("")
    L.append(f"- মোট advice পোস্ট (এই ভার্সনে): **{n}**")
    L.append(f"- মোট কমেন্ট: **{total_c}** · গড়: **{avg:.1f}**/পোস্ট · শূন্য-কমেন্ট পোস্ট: {zero}")
    L.append(f"- গভীর কর্পাসে ঢুকেছে: {len(corpus_slugs)}টা পোস্ট")
    L.append("")
    L.append("## টপ ২০ — সবচেয়ে বেশি আলোচিত (engagement ranking)")
    L.append("")
    L.append("| # | কমেন্ট | তারিখ | টাইটেল |")
    L.append("|---|---|---|---|")
    for i, r in enumerate(top, 1):
        star = " ★" if r["slug"] in corpus_slugs else ""
        L.append(f"| {i} | **{r['comments']}** | {r['date']} | [{r['title']}]({wb(r['ym'], r['slug'])}){star} |")
    L.append("")
    L.append("★ = পুরো কনটেন্ট+কমেন্ট `advice-corpus/` ফোল্ডারে সেভ করা আছে")
    L.append("")
    L.append("## পুরো লিস্ট (নতুন → পুরনো, কালানুক্রমিক)")
    L.append("")
    L.append("| তারিখ | টাইটেল | কমেন্ট |")
    L.append("|---|---|---|")
    for r in sorted(rows, key=lambda r: r["date"], reverse=True):
        L.append(f"| {r['date']} | [{r['title']}]({wb(r['ym'], r['slug'])}) | {r['comments']} |")
    L.append("")
    L.append("## Engagement প্যাটার্ন (এখন পর্যন্ত ডেটা থেকে)")
    L.append("")
    L.append("1. **প্রশ্ন-জাতীয়/interactive পোস্ট সবচেয়ে বেশি কমেন্ট পায়** — যেখানে Simon নিজে পাঠককে প্রশ্ন ছুড়ে দিয়েছেন")
    L.append("   (উদা. 'plethora' পার্ট ১: ১২, learning environment পার্ট ১: ১৮, linking experiment: ২২, vocabulary mindset quiz: ২৭)।")
    L.append("2. **দুই-পর্বের সিরিজ ভালো কাজ করে** — পার্ট ১-এ প্রশ্ন, পার্ট ২-তে উত্তর; আলোচনা দুই দিন চলে।")
    L.append("3. **'মিথ ভাঙা' পোস্টও ভাইরাল** — big words don't impress (১৮), don't use these phrases, moreover/furthermore-bashing।")
    L.append("4. **নিরবচ্ছিন্ন পড়ার মতো পোস্ট কম কমেন্ট পায়** (০–৫) — মানে comment আসে আলোচনার সুযোগ থেকে, তথ্য দিলে নয়।")
    L.append("   → আমাদের ব্লগেও প্রতি পোস্টের শেষে স্পষ্ট প্রশ্ন রাখা সবচেয়ে বড় শিক্ষা।")
    L.append("")
    L.append("## গভীর কর্পাস ইনডেক্স")
    L.append("")
    L.append("প্রতিটা এন্ট্রি = পোস্টের আসল আর্কাইভ লিংক (ক্লিকেবল) + লোকাল কর্পাস ফাইল (কনটেন্ট+কমেন্ট ফুল)।")
    L.append("")
    if corpus_files:
        title_by_slug = {r["slug"]: r["title"] for r in rows}
        for f in corpus_files:
            if not f.endswith(".md"):
                continue
            d, slug, nc = f[:-3].split("_", 2)
            ncount = nc[:-1] if nc.endswith("c") else nc
            title = title_by_slug.get(slug, slug)
            # কর্পাস ফাইলের হেডার থেকে এক্সাক্ট wayback লিংক বের করি; না পেলে জেনেরিক 2024-লিংক
            url = wb(f"{d[:4]}/{d[5:7]}", slug)
            try:
                head = open(os.path.join(CORPUS_DIR, f), encoding="utf-8").read(600)
                m = re.search(r"\((https://web\.archive\.org/web/[^)]+)\)", head)
                if m:
                    url = m.group(1)
            except OSError:
                pass
            L.append(f"- [{title} — {d}, {ncount} কমেন্ট]({url}) · `{f}`")
    else:
        L.append("- (এখনো খালি)")
    L.append("")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"wrote {OUT}: {n} posts, total {total_c} comments, avg {avg:.1f}")

if __name__ == "__main__":
    main()
