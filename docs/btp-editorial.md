# BTP hourly editor

## User brief

Find material the editor can actually publish to @bythepulse. The requested fields are domestic/overseas football, widely interesting current affairs, idols, and major sports news. The user rejected a feed of articles and generic popular posts. Discovery volume and a community name do not establish editorial value.

Read this file before every research run. The agent performs current web research and source review. Python validates and delivers that review; it does not infer editorial suitability from names or keyword scores. Do not describe this as an Instagram performance prediction model.

## Account evidence checked on 2026-10-17

Instagram's logged-out profile provided its description and counts but not the recent grid. Seven individual public post pages did provide the account owner, caption, publication date, and displayed likes/comments. Six were discovered in a public directory and one through a search-indexed discussion. This is a selected sample, not a random recent sample, a complete top-post ranking, or a recent-30-post audit.

| Post | Publication date shown | Likes shown | Comments shown | Observable editorial frame |
| --- | --- | --- | --- | --- |
| https://www.instagram.com/p/Dcn3e9hCRyY/ | 2026-08-29 | 57K | 1,988 | Widely recognized actor, unexpected major news |
| https://www.instagram.com/p/DdggK1liZn3/ | 2026-09-20 | 36K | 168 | Public apology after conflict; a clear change in behavior |
| https://www.instagram.com/p/DeCSFHGCeo9/ | 2026-10-03 | 26K | 1,946 | Young footballer with a discharge cap after a gold medal; a visual contrast |
| https://www.instagram.com/p/DanBP-8CQzE/ | 2026-07-10 | 26K | 1,175 | Stated selection interest versus actual squad omission |
| https://www.instagram.com/p/DanRAGfCXYY/ | 2026-07-10 | 25K | 293 | Footballer's like/unlike on an unfavorable ranking; an unexpected response |
| https://www.instagram.com/p/DcV0waViflq/ | 2026-08-22 | 21K | 529 | Celebration followed by a booking; action and consequence |
| https://www.instagram.com/p/DdvdAbxiZNG/ | 2026-09-26 | 5,364 | 878 | Concrete public-interest incident with discussion outside the account |

These are descriptions of BTP's published framing, not independent verification of every underlying claim. K is the rounded display from Instagram. Counts are cumulative, posts have different ages/exposure, and cannot be used to calculate a causal uplift. No reach, saves, sends, retention, or Instagram Insights were available. A third-party directory's explicitly labelled example dashboard numbers were NOT used. Threads views are NOT Instagram views.

The user's positive reference is `https://m.fmkorea.com/best/10454601662` (Red Velvet subtitle feedback). The useful pattern is an understandable before/after visual with a fan request. Do not infer that one post caused a later edit or that the event happened on an image/list timestamp.

## Editorial judgment

Recommend by two paths:

1. **A concrete shareable scene:** a recognizable person/team/group, a specific action, and a clear surprise, contrast, reaction, or consequence. Explain what a viewer sees, not just that there is a video or many comments.
2. **A genuinely major confirmed development:** an official signing, title/record, serious broadly relevant event, consequential change, or other news whose importance stands without a joke. A sports-name match, routine result, minor interview, or ordinary price change is insufficient.

For each potential first pick answer: **Who would send this to whom, and what exactly makes it worth sending now?** This is an editorial hypothesis. Meta describes share predictions as one of several recommendation inputs; it does not establish a BTP-specific cause or guarantee reach. See https://about.fb.com/news/2023/06/how-ai-ranks-content-on-facebook-and-instagram/ and https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/ .

Open sources and inspect their actual body/media. A search snippet is a lead. Find the original official account, match clip, interview, broadcast, announcement, or other primary source where possible. Read a community post's material, then corroborate factual allegations using original sources or reliable reporting. An unviewed X URL is a source link, not a video the agent has watched. Do not pass a protected FM page off as having read its body; find an accessible cited copy or original.

Reject routine rankings, generic fan opinions, old highlights disguised as new, undated media, fabricated metrics, rumors presented as fact, and posts with no concrete publishing angle. A high cumulative view count is not evidence of current acceleration. Say a clip is resurfacing only when current evidence supports that; label its original date separately. Do not automatically exclude major news merely because it is an article, or select a post merely because it is from a forum.

Search all four fields every hour, across Korean communities, original social/video posts, official sports/artist accounts, and reliable news. Also use English searches for overseas football and major sports. Practical coverage is broad and recorded, not literally the entire internet. Aim to inspect at least 12 plausible candidates on at least 6 domains before selecting; if sources fail, record the gaps. Do not force one pick per category or ten picks overall. Choose 1-5 strong recommendations, ranked; if none survive, send an honest short empty edition.

## Hourly operation

- Existing GitHub collection refreshes `data/candidates.json` and public history. It has no Telegram credentials and does not choose the report.
- The existing ChatGPT hourly task does fresh web research, reads this brief and public recent decisions, checks the account for prior coverage where accessible, and writes `data/editorial-picks.json` plus a version-2 request in ONE commit.
- Research begins before the hour. A request can prepare the upcoming hour only during its final 20 minutes; the receiver waits until the boundary. Delayed work serves the actual current hour and never replays missed hours.
- The delivery workflow pins BOTH files from the triggering commit. `editorial_sha256` binds the exact UTF-8 bytes of the picks file, including its trailing newline.
- Current-hour recovery version 1 is still accepted, but production delivery requires a matching reviewed edition. No keyword-selected fallback report is sent when an edition is missing.
- `curated_report.py` uses the existing approved-group check and encrypted common hourly/content ledger. It suppresses already-sent, partial, and uncertain deliveries. It adds stable event identities so a different caption/site cannot reset the same incident. Credentials and encrypted data remain in the workflow only.
- `data/state.json` records actual v7 delivery and the public titles/URLs/event identities selected. `data/editorial-history.json` keeps seven days of public sent/uncertain editorial decisions so the next researcher can reuse event identities. A source or test log is not delivery evidence. `/info` gives the agent's verification notes, reason for freshness, publishing angle, original materials, and cautions.

## Exact picks schema

```json
{
  "version": 1,
  "hour_utc": "YYYYMMDDHH",
  "reviewer": "ChatGPT",
  "generated_at": 1792235100,
  "coverage": {
    "queries": ["actual football search", "actual idol search", "actual current-affairs search", "actual major-sports search"],
    "opened_urls": ["https://example.org/actually-opened-source"],
    "unavailable": []
  },
  "picks": [
    {
      "title": "Accurate proposed BTP headline, at most 90 characters",
      "category": "축구",
      "url": "https://example.org/actually-opened-source",
      "source": "Source name, at most 40 characters",
      "kind": "community",
      "event_key": "stable-person-event-original-date",
      "why": "Specific reason this fits BTP and is worth sharing; at most 180 characters",
      "angle": "Concrete frame and order for the editor to build; at most 150 characters",
      "why_now": "Source date, recent development or observed current spread; at most 180 characters",
      "verified_at": 1792235100,
      "published_at": null,
      "evidence": [{"url": "https://example.org/actually-opened-source", "note": "What was actually confirmed, at most 220 characters"}],
      "materials": [{"url": "https://example.org/actually-opened-source", "label": "원문 자료", "kind": "source"}],
      "caution": "Any material unverified detail, at most 150 characters; empty when none"
    }
  ],
  "empty_reason": ""
}
```

Category is exactly one of `시사`, `축구`, `메이저 스포츠`, `아이돌`. Kind is `community`, `social`, `official`, or `article`. Each pick has 1-3 checked evidence objects and 0-3 materials. Material kind is `image`, `video`, or `source`; use `video` only if the actual video was inspected. All source, evidence and material URLs must appear in `coverage.opened_urls`; only public HTTPS URLs are accepted. Do not list a failed/blocked URL as opened. Use an accessible source/copy as the main URL instead.

`published_at` is a verified source publication epoch or null, never an inferred incident time. `verified_at` is the actual time the source was opened. Review age cannot exceed 75 minutes and preparation cannot precede the target by more than 20 minutes. `event_key` identifies the underlying event, not the new headline; reuse earlier keys from history/state. For a genuinely new follow-up, explain the new fact in `why_now` and use a new event key.

`coverage.queries`: 4-40 actual searches. `opened_urls`: up to 80. `unavailable`: up to 30 short source failure descriptions. Empty `picks` requires a concrete `empty_reason` (at most 160 characters). All text is bounded and escaped by the receiver. No Markdown or Telegram HTML belongs in the JSON fields.

Request format, with a final newline:

```json
{"version":2,"hour_utc":"YYYYMMDDHH","editorial_sha256":"sha256 of exact editorial-picks.json UTF-8 bytes"}
```

Use `github_create_tree` with the latest main tree, create a commit whose sole parent is the current head, and update main with `expected_sha` and `force=false`. Include only the two data files. If the lease fails, read the new state/request before deciding whether a write is still needed. Never force push, edit credentials, clear the ledger, or resend a completed hour.

No diagnostic/test messages or automatic Instagram uploads are authorized by this pipeline. Preserve one compact Telegram message per hour.
