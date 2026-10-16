#!/usr/bin/env python3
"""
Build master/08-simon-video-course-transcripts.md from the per-video transcript
files in scrape/simon-youtube/transcripts/<module>/NN-slug.md.

Each transcript file is produced by scrape/simon-youtube/fetch_transcripts.py and
carries YAML-ish front matter (module, index, title, video_id, duration, url,
transcript_coverage) plus a '## Description' block (the video's own summary,
which covers the whole video) and a '## Transcript' block (the spoken caption
track).

Output: master/08-simon-video-course-transcripts.md
Re-run after adding/refreshing transcripts.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TRANSCRIPTS_DIR = HERE / "transcripts"
TSV = HERE / "raw-playlists.tsv"
OUT = REPO / "master" / "08-simon-video-course-transcripts.md"

MODULES = ["reading", "listening", "speaking"]
MODULE_BN = {
    "reading": "Reading",
    "listening": "Listening",
    "speaking": "Speaking",
}

# module -> (youtube playlist id, playlist title, the master doc it feeds)
PLAYLISTS = {
    "reading": ("PLI3S3xWA78UXPuVlxzRBuoknHjbfO-ibf", "IELTS Simon Reading", "master/03-reading-master.md"),
    "listening": ("PLI3S3xWA78UUTrLytatIQVwZDwugGAzVh", "IELTS Simon Listening", "master/04-listening-master.md"),
    "speaking": ("PLI3S3xWA78UXXz0m6QoGyc-8UvHeAYTYT", "IELTS SIMON SPEAKING", "master/02-speaking-master.md"),
}

TIME_RE = re.compile(r"\d{1,2}:\d{2}")


def parse_front_matter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    meta: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip().strip('"')
    return meta


def parse_sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    parts = re.split(r"^## ", text, flags=re.M)
    for part in parts[1:]:
        name, _, body = part.partition("\n")
        out[name.strip().lower()] = body.strip()
    return out


def key_points(description: str) -> list[str]:
    """
    Pull the timestamped 'key point' lines out of a video description.
    The descriptions on the mirror channel are structured summaries with time
    ranges -- those lines are the compressed version of the whole lesson.
    """
    lines = [ln.strip().lstrip("-*• ").strip() for ln in description.splitlines()]
    lines = [ln for ln in lines if ln]
    stamped = [ln for ln in lines if TIME_RE.search(ln)]
    if stamped:
        return stamped
    # no time codes -> fall back to every non-empty line that is not a hashtag
    return [ln for ln in lines if not ln.startswith("#")][:12]


def load_module(module: str) -> list[dict]:
    folder = TRANSCRIPTS_DIR / module
    if not folder.is_dir():
        return []
    out = []
    for md in sorted(folder.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        meta = parse_front_matter(text)
        sections = parse_sections(text)
        desc = sections.get("description", "")
        desc = re.sub(r"^```|```$", "", desc, flags=re.M).strip()
        transcript = sections.get("transcript", "")
        words = len(transcript.split())
        out.append(
            {
                "meta": meta,
                "path": md,
                "rel": md.relative_to(REPO).as_posix(),
                # link relative to the output document (master/), not the repo root
                "link": "../" + md.relative_to(REPO).as_posix(),
                "description": desc,
                "transcript_words": words,
                "key_points": key_points(desc),
                "coverage": meta.get("transcript_coverage", "n/a"),
            }
        )
    out.sort(key=lambda d: int(d["meta"].get("index", 0)))
    return out


def to_seconds(duration: str) -> int:
    parts = [int(p) for p in duration.split(":") if p.isdigit()]
    if not parts:
        return 0
    total = 0
    for p in parts:
        total = total * 60 + p
    return total


def human(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} ঘণ্টা {m} মিনিট"
    return f"{m} মিনিট {s} সেকেন্ড" if s else f"{m} মিনিট"


def main() -> None:
    L: list[str] = []
    L.append("---")
    L.append('title: "IELTS Simon ভিডিও কোর্স — Reading, Listening ও Speaking প্লেলিস্ট ট্রান্সক্রিপ্ট (গোছানো সংগ্রহ)"')
    L.append('slug: "ielts-simon-video-course-transcripts"')
    L.append('meta_title: "IELTS Simon Video Course Transcripts | Reading, Listening, Speaking"')
    L.append('meta_description: "IELTS Simon-এর Reading (১০ লেসন), Listening (২ লেসন) ও Speaking (৬ লেসন) ভিডিও কোর্সের পূর্ণ ট্রান্সক্রিপ্ট — লেসন-ভিত্তিক মূল কৌশল, ভোকাবুলারি থিম ও টেকনিক বিজ্ঞানী বাংলায়।"')
    L.append('keywords: ["ielts simon transcript", "ielts reading transcript", "ielts listening transcript", "ielts speaking transcript", "ielts video course"]')
    L.append('module: "Reference / Video Course"')
    L.append(f"generated: {date.today().isoformat()}")
    L.append("---")
    L.append("")
    L.append("# IELTS Simon ভিডিও কোর্স — প্লেলিস্ট ট্রান্সক্রিপ্ট (Reading → Listening → Speaking)")
    L.append("")
    L.append(
        "> **সোর্স:** YouTube-এর তিনটি কোর্স প্লেলিস্ট — *IELTS Simon Reading*, *IELTS Simon Listening*, *IELTS SIMON SPEAKING*। "
        "ভিডিওগুলো মূলত ielts-simon.com থেকে এসেছে (সেই সাইট এখন বন্ধ; মেম্বার সাইট: ielts-simon.study)। "
        "স্ক্র্যাপার: `scrape/simon-youtube/fetch_transcripts.py` · ডেটা: `scrape/simon-youtube/transcripts/` · "
        "প্লেলিস্ট লিস্টিং: `scrape/simon-youtube/raw-playlists.tsv`।"
    )
    L.append(">")
    L.append(
        "> **ফাইল স্ট্রাকচার:** প্রতিটি ভিডিও = একটি মার্কডাউন ফাইল — ফ্রন্ট-ম্যাটার (duration, link, coverage) + "
        "**Description** (পুরো ভিডিওর টাইমস্ট্যাম্পড সারাংশ) + **Transcript** (সায়েমনের আসল কথা, caption থেকে)।"
    )
    L.append(">")
    L.append(
        "> **কভারেজ নোট:** YouTube-এর caption ট্র্যাক থেকে ট্রান্সক্রিপ্ট নেওয়া হয়েছে; দীর্ঘ লেসনে "
        "reader-এর সীমার কারণে ট্রান্সক্রিপ্ট প্রায় ৫০–৮০% পর্যন্ত এসেছে। প্রতিটি ফাইলে কোন সময় পর্যন্ত "
        "পাওয়া গেছে (`transcript_coverage`) স্পষ্ট লেখা আছে, এবং বাকি অংশের সারাংশ Description-এ টাইমস্ট্যাম্পসহ আছে।"
    )
    L.append("")

    modules = {m: load_module(m) for m in MODULES}

    # ---------------- এক নজরে ----------------
    L.append("## এক নজরে")
    L.append("")
    L.append("| মডিউল | লেসন সংখ্যা | মোট দৈর্ঘ্য | প্লেলিস্ট লিংক | ফিড মাস্টার |")
    L.append("|---|---|---|---|---|")
    for m in MODULES:
        items = modules[m]
        pid, ptitle, master_doc = PLAYLISTS[m]
        total = sum(to_seconds(i["meta"].get("duration", "0")) for i in items)
        L.append(
            f"| {MODULE_BN[m]} | {len(items)} | {human(total)} | "
            f"[{ptitle}](https://www.youtube.com/playlist?list={pid}) | "
            f"→ `{master_doc}` |"
        )
    L.append("")

    total_videos = sum(len(modules[m]) for m in MODULES)
    L.append(
        f"**মোট {total_videos}টি ভিডিও · ৩টি প্লেলিস্ট · {total_videos}টি ট্রান্সক্রিপ্ট ফাইল।**"
    )
    L.append("")

    # ---------------- মডিউল ভিত্তিক সেকশন ----------------
    for m in MODULES:
        items = modules[m]
        if not items:
            continue
        pid, ptitle, master_doc = PLAYLISTS[m]
        L.append("---")
        L.append("")
        L.append(f"## {MODULE_BN[m]} ({len(items)} লেসন)")
        L.append("")
        L.append(f"**প্লেলিস্ট:** [{ptitle}](https://www.youtube.com/playlist?list={pid})")
        L.append("")
        L.append("| # | লেসন | দৈর্ঘ্য | ট্রান্সক্রিপ্ট | ভিডিও | কভারেজ |")
        L.append("|---|---|---|---|---|---|")
        for it in items:
            meta = it["meta"]
            L.append(
                f'| {meta.get("index","")} | {meta.get("title","")} | {meta.get("duration","")} | '
                f'[`{Path(it["rel"]).name}`]({it["link"]}) | [YT]({meta.get("url","")}) | {it["coverage"]} |'
            )
        L.append("")

        L.append("### লেসন-ভিত্তিক মূল পয়েন্ট")
        L.append("")
        for it in items:
            meta = it["meta"]
            L.append(f'#### {meta.get("index","")}. {meta.get("title","")} ({meta.get("duration","")})')
            L.append("")
            L.append(f'ভিডিও: {meta.get("url","")} · ফাইল: `{it["rel"]}`')
            L.append("")
            for kp in it["key_points"]:
                L.append(f"- {kp}")
            L.append("")

    # ---------------- কীভাবে ব্যবহার করবেন ----------------
    L.append("---")
    L.append("")
    L.append("## এই সংগ্রহটি কীভাবে ব্যবহার করবেন")
    L.append("")
    L.append(
        "১. **ডেস্ক্রিপশন-বেজড স্ট্রাকচার।** প্রতিটি লেসন আগে 'technique/ভিত্তি' তারপর 'example/উদাহরণ' "
        "ধাপে যায় — বাংলা ব্লগে একই ক্রম (কৌশল আগে, তারপর উদাহরণ) মানায়।"
    )
    L.append(
        "২. **ভোকাবুলারি থিম ব্যাংক।** Speaking প্লেলিস্টে সাইমন প্রতিটি টপিকে 'theme + example' বানিয়েছেন "
        "(যেমন swimming / chess / watch / London) — এগুলো আমাদের মাস্টার-০২-এর কিউ-কার্ড ব্যাংকের সঙ্গে জোড়া লাগে।"
    )
    L.append(
        "৩. **কীওয়ার্ড টেবিল প্র্যাকটিস।** Reading ও Listening-এর প্রতিটি লেসন শেষে সাইমন বলেছেন — "
        "'synonym টেবিল' বানাও (যেমন shaded → damp, moist)। এটা বাংলাদেশি স্টুডেন্টদের জন্য চমৎকার ধারাবাহিক টাস্ক।"
    )
    L.append(
        "৪. **ব্যান্ড ডেসক্রিপ্টর-ভিত্তিক উপদেশ।** Speaking লেসনে সাইমন স্কোরিং ক্রাইটেরিয়া (FC / LR / GRA / PR) "
        "নিজের ভাষায় ব্যাখ্যা করেছেন — master-০২-এর descriptor-কোট সেকশনের ভিডিও-সোর্স হিসেবে ব্যবহার করা যায়।"
    )
    L.append(
        "৫. **সতর্কতা।** ট্রান্সক্রিপ্টগুলো YouTube-এর অটো-ক্যাপশন থেকে নেওয়া, তাই কিছু শব্দ ভুল "
        "(যেমন 'scam' → 'scam'/'scheme')। উদ্ধৃতি দেওয়ার আগে ইংরেজি টেক্সটটা মিলিয়ে নিতে হবে।"
    )
    L.append("")

    # ---------------- সূত্র / পদ্ধতি ----------------
    L.append("## সূত্র ও পদ্ধতি")
    L.append("")
    L.append("- **মূল চ্যানেল:** [IELTS Simon (@ieltssimonofficial)](https://www.youtube.com/@ieltssimonofficial) — মূল সাইট ielts-simon.com এখন বন্ধ, তাই ভিডিওগুলো মিরর চ্যানেল [IELTS Albert (@TheIELTSListeningTest2026)](https://www.youtube.com/@TheIELTSListeningTest2026)-এ আছে।")
    L.append("- **কোর্স সাইট:** [ielts-simon.study](https://ielts-simon.study/) — একই লেসনগুলোর লেখা ভার্সন (মেম্বার সাইট)।")
    L.append("- **কোর্স ম্যাপ:** [master/07-simon-content-index.md](07-simon-content-index.md) — ielts-simon.study-র ১০টি index ট্যাব ও ৪৭টি ভিডিও কোর্স লেসনের পূর্ণ তালিকা।")
    L.append("- **পুরনো ব্লগ আর্কাইভ:** [master/07a-simon-oldblog-archive-index.md](07a-simon-oldblog-archive-index.md) — Wayback Machine-এ ielts-simon.com-এর পুরনো লেখা।")
    L.append(f"- **স্ক্র্যাপার:** `scrape/simon-youtube/fetch_transcripts.py` (নেটওয়ার্ক লাগে) + `scrape/simon-youtube/build-transcripts-doc.py` (অফলাইন, এই ডক বানায়)।")
    L.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    for m in MODULES:
        print(f"  {m:10} {len(modules[m])} lessons")


if __name__ == "__main__":
    main()
