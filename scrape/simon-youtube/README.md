# scrape/simon-youtube — IELTS Simon ভিডিও কোর্সের ট্রান্সক্রিপ্ট সংগ্রহ

সাইমনের YouTube কোর্স প্লেলিস্টগুলোর (Reading → Listening → Speaking) ক্যাপশন
ট্রান্সক্রিপ্ট স্ক্র্যাপ করে গোছানোভাবে রাখার জায়গা।

## সোর্স

| মডিউল | প্লেলিস্ট | ভিডিও | চ্যানেল |
|---|---|---|---|
| Reading | [IELTS Simon Reading](https://www.youtube.com/playlist?list=PLI3S3xWA78UXPuVlxzRBuoknHjbfO-ibf) | ১০ | IELTS Albert (`@TheIELTSListeningTest2026`) |
| Listening | [IELTS Simon Listening](https://www.youtube.com/playlist?list=PLI3S3xWA78UUTrLytatIQVwZDwugGAzVh) | ২ | ঐ |
| Speaking | [IELTS SIMON SPEAKING](https://www.youtube.com/playlist?list=PLI3S3xWA78UXXz0m6QoGyc-8UvHeAYTYT) | ৬ | ঐ |

মূল চ্যানেল `@ieltssimonofficial`-এর কপিগুলো আর পাওয়া যায় না, তাই মিরর চ্যানেল
ব্যবহার করা হয়েছে (ভিডিও ID একই, তাই লিংক কাজ করে)। একই কোর্সের লেখা ভার্সন
[ielts-simon.study](https://ielts-simon.study/)-তে আছে।

## ফাইল কাঠামো

```
scrape/simon-youtube/
├── README.md                  ← এই ফাইল
├── raw-playlists.tsv          ← ১৮টি ভিডিওর প্লেলিস্ট লিস্টিং (ট্যাব-সেপারেটেড)
├── fetch_transcripts.py       ← স্ক্র্যাপার (yt-dlp + youtube-transcript-api)
├── build-transcripts-doc.py   ← মাস্টার ডক জেনারেটর (অফলাইন)
└── transcripts/
    ├── reading/   01…10-*.md
    ├── listening/ 01…02-*.md
    └── speaking/  01…06-*.md
```

## একটি ট্রান্সক্রিপ্ট ফাইলের ভেতরে

প্রতিটি ফাইলে তিনটি অংশ:

1. **ফ্রন্ট-ম্যাটার** — `module`, `index`, `title`, `video_id`, `duration`, `playlist`,
   `playlist_title`, `url`, `uploaded_by`, `uploaded_at`, `scraped`,
   `transcript_coverage`
2. **`## Description`** — ভিডিওর নিজস্ব টাইমস্ট্যাম্পড সারাংশ (পুরো লেসন কভার করে)
3. **`## Transcript`** — ক্যাপশন থেকে নেওয়া সাইমনের আসল কথা

### `transcript_coverage` — কভারেজ সৎভাবে লেখা

| মান | মানে |
|---|---|
| `complete` | পুরো ভিডিওর ক্যাপশন পাওয়া গেছে |
| `0:00 - ~17:06 (caption track as published; remainder summarised in Description)` | ক্যাপশন ১৭:০৬ পর্যন্ত এসেছে; বাকি অংশের সারাংশ Description-এ আছে |

ফাইলের ট্রান্সক্রিপ্ট সেকশনের শুরুতে একটি `>` ব্লক-কোট নোটে একই কভারেজ
লেখা থাকে — কখনোই আংশিক ক্যাপশনকে সম্পূর্ণ হিসেবে দেখানো হয় না।

## ব্যবহার

### নতুন করে স্ক্র্যাপ (নেটওয়ার্ক লাগে)

```bash
pip install yt-dlp youtube-transcript-api

python3 scrape/simon-youtube/fetch_transcripts.py --module reading
python3 scrape/simon-youtube/fetch_transcripts.py --all        # reading → listening → speaking
```

অপশন: `--out DIR` (মার্কডাউন আউটপুট), `--raw DIR` (raw json ক্যাশ),
`--skip-existing` (মান ফাইল ওভাররাইট না করা)।

### ট্রান্সক্রিপ্ট প্যারাগ্রাফে সাজানো (অফলাইন)

```bash
python3 scrape/simon-youtube/fetch_transcripts.py --normalize
```

~৪০-ক্যার হার্ড-ওয়্যাপড ক্যাপশন লাইনগুলোকে পড়ার-উপযোগী প্যারাগ্রাফে জোড়া লাগায়।
ফ্রন্টের কভারেজ নোট অক্ষত থাকে।

### মাস্টার ডক বানানো (অফলাইন)

```bash
python3 scrape/simon-youtube/build-transcripts-doc.py
# → master/08-simon-video-course-transcripts.md
```

## সীমাবদ্ধতা

- ট্রান্সক্রিপ্ট YouTube-এর **অটো-ক্যাপশন** থেকে নেওয়া, তাই কিছু শব্দ ভুল লেখা
  থাকতে পারে; উদ্ধৃতি দেওয়ার আগে ইংরেজি টেক্সট মিলিয়ে নিতে হবে।
- দীর্ঘ লেসনে (৮–৩৩ মিনিট) reader-এর সীমার কারণে ক্যাপশন প্রায় ৫০–৮০% পর্যন্ত
  এসেছে; বাকি অংশ Description-এর টাইমস্ট্যাম্পড সারাংশে আছে।
- `youtube.com/api/timedtext` ও বিভিন্ন তৃতীয় ট্রান্সক্রিপ্ট API এই স্যান্ডবক্সে
  ব্লকড, তাই ফেচ করা হয়েছে watch-পেজের reader আউটপুট থেকে।
