# IELTS Content System — Bangla (মাদারি স্টাইল)

এটা একটা **কমপ্লিট কনটেন্ট সিস্টেম** (৩ টায়ার):

- **Tier 0 — Master Write-up** (`../master/`): অথরিটেটিভ, কমপ্রিহেনসিভ নলেজ বেস। "১০-মিনিট গাইড" স্টাইল, কোটেড official band descriptors + কোশ্চেন/পার্ট-ওয়াইজ স্ট্রাটেজি। সোর্স অফ ট্রুথ।
- **Tier 1 — Derived Blog** (`blogs/01..04`): ইঞ্গেজিং, কলোকোয়াল বাংলা ব্লগ। মাস্টার থেকে স্পিন-অফ।
- **Tier 2 — Template** (`../templates/blog-template.md`): দ্রুত প্রডাকশন স্কেলটন।

---

## Tier 0 — Master Write-ups (`master/`)

| # | নতুন নাম ("A Complete Guide to X for Bangladeshi Students") | ফাইল | Slug |
|---|-------|------|------|
| ০ | A Complete Guide to IELTS Preparation for Bangladeshi Students | `master/00-master-framework.md` | `complete-guide-ielts-preparation-bangladeshi-students` |
| ১ | A Complete Guide to IELTS Writing for Bangladeshi Students | `master/01-writing-master.md` | `complete-guide-ielts-writing-bangladeshi-students` |
| ২ | A Complete Guide to IELTS Speaking for Bangladeshi Students | `master/02-speaking-master.md` | `complete-guide-ielts-speaking-bangladeshi-students` |
| ৩ | A Complete Guide to IELTS Reading for Bangladeshi Students | `master/03-reading-master.md` | `complete-guide-ielts-reading-bangladeshi-students` |
| ৪ | A Complete Guide to IELTS Listening for Bangladeshi Students | `master/04-listening-master.md` | `complete-guide-ielts-listening-bangladeshi-students` |
| ৫ | BD কনটেন্ট প্ল্যান (internal) | `master/05-bd-content-plan.md` | `bd-ielts-content-traffic-plan` |
| ৬ | টপ-রিড আর্টিকেল + ট্রাফিক/গ্যাপ রিসার্চ (internal) | `master/06-top-read-articles-and-gap-research.md` | `top-ielts-articles-bangladesh-traffic-gap-research` |
| ৭ | IELTS Simon কনটেন্ট ইনডেক্স + আর্কাইভ (reference) | `master/07-simon-content-index.md` | `ielts-simon-complete-content-index-archive` |

**নামকরণ কনভেনশন:** পিলার আর্টিকেলের নাম **"A Complete Guide to X for Bangladeshi Students"** ফরম্যাটে (+ ফি/ডেট পেইজে বছর)। রিকারিং পেইজে মাস-বছর ট্যাগ — যেমন "Recent IELTS Speaking Questions in Bangladesh — October 2026"। প্রতিটার বাংলা মিরর ভার্সন। বিস্তারিত রিসার্চ ও নতুন ২০টা আর্টিকেলের নাম: `master/06-top-read-articles-and-gap-research.md`।

প্রতিটা মাস্টার ডকে: কনটেক্সট → মাস্ট-নো ফ্যাক্টস → ওভারঅল ট্যাকলিং স্ট্রাটেজি → কোশ্চেন/পার্ট-ওয়াইজ স্ট্রাটেজি → টিপস অ্যান্ড ট্রিকস → ১-সপ্তাহ প্ল্যান। অথরিটি: official band descriptors (কোট) + Pauline Cullen (The Key to IELTS Success ফ্রি PDF) + Chris Pell (IELTS Advantage)।

## Tier 1 — Derived Blogs (`blogs/`)

| # | মডিউল | ফাইল | Slug |
|---|-------|------|------|
| ১ | Writing | `01-ielts-writing.md` | `ielts-writing-7-band-guide-bangla` |
| ২ | Speaking | `02-ielts-speaking.md` | `ielts-speaking-7-band-guide-bangla` |
| ৩ | Reading | `03-ielts-reading.md` | `ielts-reading-7-band-guide-bangla` |
| ৪ | Listening | `04-ielts-listening.md` | `ielts-listening-7-band-guide-bangla` |
| ৫ | Preparation Roadmap — ঘরে বসে IELTS এর পূর্ণ প্রস্তুতি (Tier A #2, রিসোর্স-লিস্ট + রোডম্যাপ) | `05-ghore-boshe-ielts-er-purno-prostuti.md` | `ghore-boshe-ielts-er-purno-prostuti` |

প্রতিটা ব্লগে SEO (title, slug, meta), AEO (FAQ), ফ্রন্ট-ম্যাটার আছে। স্ট্রাকচার: Hook → কনটেক্সট → সমস্যা → ফ্রেমওয়ার্ক → Common Mistakes → ৭-দিন প্ল্যান → চেকলিস্ট → FAQ।

## নতুন ব্লগ দ্রুত বানাতে

`../templates/blog-template.md` কপি করুন আর {{placeholder}} গুলো ভরে ফেলুন।
