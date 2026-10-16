#!/usr/bin/env python3
"""
IELTS Simon video-course transcript scraper.

Pulls the *playlist* listings + the full spoken transcript of every video in
Simon's three course playlists (Reading -> Listening -> Speaking) and writes one
organised markdown file per video:

    scrape/simon-youtube/transcripts/<module>/<NN>-<slug>.md
    scrape/simon-youtube/raw-playlists.tsv      (playlist listing, appended)

Sources
-------
* Playlists live on the YouTube mirror channel "IELTS Albert"
  (@TheIELTSListeningTest2026) which re-hosts the original ielts-simon.com
  course videos. The original channel is https://www.youtube.com/@ieltssimonofficial
  and the same course is on the member site https://ielts-simon.study/
* Transcripts are the YouTube caption tracks (auto-generated where Simon did
  not publish a written transcript).

Usage
-----
    pip install yt-dlp youtube-transcript-api

    # one module
    python3 scrape/simon-youtube/fetch_transcripts.py --module reading

    # everything, in order
    python3 scrape/simon-youtube/fetch_transcripts.py --all

    # offline: re-flow the transcript paragraphs of existing markdown files
    python3 scrape/simon-youtube/fetch_transcripts.py --normalize

    # offline: rebuild master/08-simon-video-course-transcripts.md
    python3 scrape/simon-youtube/build-transcripts-doc.py

Options
-------
    --out DIR        where to write the markdown files (default: transcripts/)
    --raw DIR        where to cache the raw yt-dlp/transcript json (default: raw/)
    --skip-existing  do not overwrite markdown files that already exist
    --normalize      offline re-flow of the '## Transcript' paragraphs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

# --------------------------------------------------------------------------
# Playlist registry -- the three course playlists, in the order we want them.
# --------------------------------------------------------------------------
PLAYLISTS: dict[str, dict[str, str]] = {
    "reading": {
        "playlist_id": "PLI3S3xWA78UXPuVlxzRBuoknHjbfO-ibf",
        "playlist_title": "IELTS Simon Reading",
    },
    "listening": {
        "playlist_id": "PLI3S3xWA78UUTrLytatIQVwZDwugGAzVh",
        "playlist_title": "IELTS Simon Listening",
    },
    "speaking": {
        "playlist_id": "PLI3S3xWA78UXXz0m6QoGyc-8UvHeAYTYT",
        "playlist_title": "IELTS SIMON SPEAKING",
    },
}

ORIGINAL_CHANNEL = "https://www.youtube.com/@ieltssimonofficial"
COURSE_SITE = "https://ielts-simon.study/"

HERE = Path(__file__).resolve().parent
TRANSCRIPTS_DIR = HERE / "transcripts"
RAW_DIR = HERE / "raw"
PLAYLIST_TSV = HERE / "raw-playlists.tsv"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def slugify(text: str) -> str:
    """'IELTS Simon Reading part 2' -> 'ielts-simon-reading-part-2'."""
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    text = re.sub(r"-{2,}", "-", text)
    return text[:70] or "video"


def seconds_to_hhmmss(seconds: int | float) -> str:
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def reflow(caption_text: str) -> str:
    """
    YouTube caption tracks arrive as ~40 char hard-wrapped lines with no
    punctuation. Rebuild readable paragraphs: join the lines, then break a new
    paragraph whenever the speaker clearly starts a new thought.
    """
    lines = [ln.strip() for ln in caption_text.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return ""

    # Re-join the hard-wrapped lines into a single stream of words.
    words: list[str] = []
    for ln in lines:
        words.extend(ln.split())

    # Rebuild sentences, then group sentences into paragraphs of ~4 sentences.
    sentences: list[str] = []
    buf: list[str] = []
    for w in words:
        buf.append(w)
        if w.endswith((".", "?", "!")):
            sentences.append(" ".join(buf))
            buf = []
    if buf:
        sentences.append(" ".join(buf))

    paras: list[str] = []
    cur: list[str] = []
    for s in sentences:
        cur.append(s)
        if len(cur) >= 4:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))

    out = []
    for p in paras:
        # Tidy the two artefacts of caption-joining: "( 2:06 )" and stray spaces
        # before punctuation.
        p = re.sub(r"\(\s*", "(", p)
        p = re.sub(r"\s*\)", ")", p)
        p = re.sub(r"\s+([,.])", r"\1", p)
        p = re.sub(r"([,.])(\S)", r"\1 \2", p)
        p = re.sub(r"\s{2,}", " ", p).strip()
        out.append(p)
    return "\n\n".join(out)


def write_markdown(path: Path, meta: dict, description: str, transcript: str) -> None:
    coverage = "complete" if transcript.strip() else "none"
    fm = [
        "---",
        f'module: {meta["module"]}',
        f'index: {meta["index"]}',
        f'title: "{meta["title"]}"',
        f'video_id: {meta["video_id"]}',
        f'duration: "{meta["duration"]}"',
        f'playlist: "{meta["playlist_id"]}"',
        f'playlist_title: "{meta["playlist_title"]}"',
        f'url: "{meta["url"]}"',
        f'uploaded_by: "{meta.get("channel", "")}"',
        f'uploaded_at: "{meta.get("upload_date", "")}"',
        f'scraped: {date.today().isoformat()}',
        f'transcript_coverage: "{coverage}"',
        "---",
        "",
    ]
    body = [
        f'# {meta["title"]}',
        "",
        f'**Video:** {meta["url"]} · {meta["duration"]} · '
        f'[Playlist: {meta["playlist_title"]}](https://www.youtube.com/playlist?list={meta["playlist_id"]})',
        f'**Channel:** {meta.get("channel", "")} · **Uploaded:** {meta.get("upload_date", "")} · '
        f'**Transcript scraped:** {date.today().isoformat()}',
        "",
        "## Description",
        "",
        description.strip() or "_(no description)_",
        "",
        "## Transcript",
        "",
        transcript.strip() or "_(no caption track available)_",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(fm + body), encoding="utf-8")


# --------------------------------------------------------------------------
# network bits (need internet + yt-dlp / youtube-transcript-api)
# --------------------------------------------------------------------------
def fetch_playlist_entries(playlist_id: str) -> list[dict]:
    """Return [{index, video_id, title, duration, url}] for a playlist."""
    try:
        from yt_dlp import YoutubeDL
    except ImportError:  # pragma: no cover
        sys.exit("yt-dlp is required: pip install yt-dlp")

    opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/playlist?list={playlist_id}", download=False
        )
    entries = []
    for i, e in enumerate(info.get("entries") or [], start=1):
        if not e:
            continue
        entries.append(
            {
                "index": i,
                "video_id": e.get("id", ""),
                "title": e.get("title", ""),
                "duration": e.get("duration") or 0,
                "url": f"https://www.youtube.com/watch?v={e.get('id','')}",
            }
        )
    return entries


def fetch_video_meta(video_id: str) -> dict:
    from yt_dlp import YoutubeDL

    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}", download=False
        ) or {}


def fetch_transcript(video_id: str) -> str:
    """Raw caption text (may be empty when the video has no caption track)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:  # pragma: no cover
        sys.exit("youtube-transcript-api is required: pip install youtube-transcript-api")

    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
    except Exception:  # noqa: BLE001 - fall back to the legacy instance API
        fetched = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
    return " ".join(snippet.text for snippet in fetched)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def run_module(module: str, out_dir: Path, raw_dir: Path, skip_existing: bool) -> None:
    cfg = PLAYLISTS[module]
    print(f"\n=== {module.upper()} :: {cfg['playlist_title']} ===")
    entries = fetch_playlist_entries(cfg["playlist_id"])
    rows = []
    for e in entries:
        raw_path = raw_dir / f"{e['video_id']}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if raw_path.exists():
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
        else:
            meta = fetch_video_meta(e["video_id"])
            raw = {
                "id": e["video_id"],
                "title": e["title"],
                "duration": e["duration"],
                "channel": meta.get("channel") or meta.get("uploader") or "",
                "upload_date": meta.get("upload_date") or "",
                "description": (meta.get("description") or "").strip(),
                "captions": fetch_transcript(e["video_id"]),
            }
            raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

        meta = {
            "module": module,
            "index": e["index"],
            "title": raw.get("title") or e["title"],
            "video_id": e["video_id"],
            "duration": seconds_to_hhmmss(raw.get("duration") or e["duration"]),
            "playlist_id": cfg["playlist_id"],
            "playlist_title": cfg["playlist_title"],
            "url": e["url"],
            "channel": raw.get("channel", ""),
            "upload_date": raw.get("upload_date", ""),
        }
        md_path = out_dir / module / f'{e["index"]:02d}-{slugify(meta["title"])}.md'
        if not (skip_existing and md_path.exists()):
            write_markdown(md_path, meta, raw.get("description", ""), reflow(raw.get("captions", "")))
            print(f"  wrote {md_path.relative_to(HERE)}")
        else:
            print(f"  skip  {md_path.relative_to(HERE)} (exists)")

        rows.append(
            [
                module,
                cfg["playlist_id"],
                cfg["playlist_title"],
                str(e["index"]),
                e["video_id"],
                meta["title"],
                meta["duration"],
                raw.get("channel", ""),
                e["url"],
            ]
        )

    # keep raw-playlists.tsv in sync
    header = [
        "module",
        "playlist_id",
        "playlist_title",
        "index",
        "video_id",
        "video_title",
        "duration",
        "channel",
        "channel_handle",
        "url",
    ]
    existing = []
    if PLAYLIST_TSV.exists():
        lines = PLAYLIST_TSV.read_text(encoding="utf-8").splitlines()
        existing = lines[1:] if lines else []
    keep = [ln for ln in existing if not ln.startswith(f"{module}\t")]
    with PLAYLIST_TSV.open("w", encoding="utf-8") as f:
        f.write("\t".join(header) + "\n")
        for ln in keep + ["\t".join(r) for r in rows]:
            f.write(ln + "\n")
    print(f"  playlist listing -> {PLAYLIST_TSV.relative_to(HERE)} ({len(rows)} videos)")


def _split_note(tail: str) -> tuple[str, str]:
    """
    Split a leading markdown blockquote (the 'transcript coverage' note) off the
    caption text so that re-flowing never eats the note.
    """
    lines = tail.split("\n")
    if not lines or not lines[0].lstrip().startswith(">"):
        return "", tail
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.lstrip().startswith(">"):
            i += 1
        elif ln.strip() == "" and i + 1 < len(lines) and lines[i + 1].lstrip().startswith(">"):
            i += 1
        else:
            break
    note = "\n".join(lines[:i]).strip()
    rest = "\n".join(lines[i:]).strip()
    return note, rest


def normalize_file(path: Path) -> bool:
    """
    Re-flow the '## Transcript' section of an existing markdown file into
    readable paragraphs (same transform the scraper applies on a fresh run).
    The leading coverage note is kept verbatim.
    Returns True when the file was changed.
    """
    text = path.read_text(encoding="utf-8")
    marker = "\n## Transcript\n\n"
    if marker not in text:
        return False
    head, tail = text.split(marker, 1)
    tail = tail.rstrip("\n")
    # keep any trailing section that might have been appended after the transcript
    extra = ""
    for tail_marker in ("\n## ", "\n# "):
        if tail_marker in tail:
            tail, extra = tail.split(tail_marker, 1)
            extra = tail_marker + extra
            break
    note, body = _split_note(tail.strip())
    new_body = reflow(body)
    if not new_body:
        return False
    new_tail = f"{note}\n\n{new_body}" if note else new_body
    updated = f"{head}{marker}{new_tail}\n{extra}".rstrip("\n") + "\n"
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def normalize_all(out_dir: Path) -> None:
    n = 0
    for md in sorted(out_dir.glob("*/*.md")):
        if normalize_file(md):
            n += 1
            print(f"  normalised {md.relative_to(HERE)}")
    print(f"normalised {n} file(s)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", choices=sorted(PLAYLISTS), help="which playlist to scrape")
    ap.add_argument(
        "--normalize",
        action="store_true",
        help="offline: re-flow the transcript paragraphs of existing markdown files",
    )
    ap.add_argument("--all", action="store_true", help="scrape reading, listening, speaking in order")
    ap.add_argument("--out", default=str(TRANSCRIPTS_DIR), help="output directory for the markdown files")
    ap.add_argument("--raw", default=str(RAW_DIR), help="cache directory for the raw json dumps")
    ap.add_argument("--skip-existing", action="store_true", help="do not overwrite existing markdown")
    args = ap.parse_args()

    modules = list(PLAYLISTS) if args.all else ([args.module] if args.module else [])
    if not modules and not args.normalize:
        ap.error("pass --module <reading|listening|speaking>, --all, or --normalize")

    out_dir = Path(args.out)
    raw_dir = Path(args.raw)
    if args.normalize:
        normalize_all(out_dir)
    for module in modules:
        run_module(module, out_dir, raw_dir, args.skip_existing)


if __name__ == "__main__":
    main()
