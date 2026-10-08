# IELTS Content System — Bangla (মাদারি স্টাইল)

এটা একটা **কমপ্লিট কনটেন্ট সিস্টেম** (৩ টায়ার):

- **Tier 0 — Master Write-up** (`../master/`): অথরিটেটিভ, কমপ্রিহেনসিভ নলেজ বেস। "১০-মিনিট গাইড" স্টাইল, কোটেড official band descriptors + কোশ্চেন/পার্ট-ওয়াইজ স্ট্রাটেজি। সোর্স অফ ট্রুথ।
- **Tier 1 — Derived Blog** (`blogs/01..04`): ইঞ্গেজিং, কলোকোয়াল বাংলা ব্লগ। মাস্টার থেকে স্পিন-অফ।
- **Tier 2 — Template** (`../templates/blog-template.md`): দ্রুত প্রডাকশন স্কেলটন।

---

## Tier 0 — Master Write-ups (`master/`)

| # | মডিউল | ফাইল | Slug |
|---|-------|------|------|
| ০ | Framework (আর্কিটেকচার/চার্ট) | `master/00-master-framework.md` | `ielts-complete-solution-master-framework` |
| ১ | Writing | `master/01-writing-master.md` | `ielts-writing-10-minute-master-guide-bangla` |
| ২ | Speaking | `master/02-speaking-master.md` | `ielts-speaking-10-minute-master-guide-bangla` |
| ৩ | Reading | `master/03-reading-master.md` | `ielts-reading-10-minute-master-guide-bangla` |
| ৪ | Listening | `master/04-listening-master.md` | `ielts-listening-10-minute-master-guide-bangla` |

প্রতিটা মাস্টার ডকে: কনটেক্সট → মাস্ট-নো ফ্যাক্টস → ওভারঅল ট্যাকলিং স্ট্রাটেজি → কোশ্চেন/পার্ট-ওয়াইজ স্ট্রাটেজি → টিপস অ্যান্ড ট্রিকস → ১-সপ্তাহ প্ল্যান। অথরিটি: official band descriptors (কোট) + Pauline Cullen (The Key to IELTS Success ফ্রি PDF) + Chris Pell (IELTS Advantage)।

## Tier 1 — Derived Blogs (`blogs/`)

| # | মডিউল | ফাইল | Slug |
|---|-------|------|------|
| ১ | Writing | `01-ielts-writing.md` | `ielts-writing-7-band-guide-bangla` |
| ২ | Speaking | `02-ielts-speaking.md` | `ielts-speaking-7-band-guide-bangla` |
| ৩ | Reading | `03-ielts-reading.md` | `ielts-reading-7-band-guide-bangla` |
| ৪ | Listening | `04-ielts-listening.md` | `ielts-listening-7-band-guide-bangla` |

প্রতিটা ব্লগে SEO (title, slug, meta), AEO (FAQ), ফ্রন্ট-ম্যাটার আছে। স্ট্রাকচার: Hook → কনটেক্সট → সমস্যা → ফ্রেমওয়ার্ক → Common Mistakes → ৭-দিন প্ল্যান → চেকলিস্ট → FAQ।

## নতুন ব্লগ দ্রুত বানাতে

`../templates/blog-template.md` কপি করুন আর {{placeholder}} গুলো ভরে ফেলুন।
