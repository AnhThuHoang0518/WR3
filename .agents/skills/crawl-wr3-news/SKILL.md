---
name: crawl-wr3-news
description: Crawl, rerun, and diagnose the canonical WR3 weekly Smart City news collection across Market, Competitor, Technology, and Policy using parallel RSS plus Web Search/source-fetch discovery. Use a citizen-experience lens for Smart City services, smart parking, smart venues and stadiums, amusement/theme parks and attractions, Digital Twins, and AI-enabled urban operations and safety; cover end-to-end user journeys, measurable friction and outcomes, and auditable source evidence without reading products.json. Also perform catalog-independent competitor discovery, dedicated China and Singapore discovery, and neutral capability query expansion. Use whenever a user working in WR3 says "crawl", "crawl news", "crawl lại news", asks to fetch or refresh recent/weekly news, or asks to inspect crawl coverage. Run the WR3 News stages and stop at News Relevance HITL; never perform Signal, Opportunity/Threat, Product Mapping, Product Gap, Action, or human approval.
---

# Crawl WR3 News

Collect the canonical WR3 News inputs through the existing stage 01-04 runtimes. Preserve the configured geographic coverage. For Competitor News, combine known-competitor tracking with catalog-independent discovery so companies outside `competitors.json` can be found and presented to Gate 1; do not interpret this rule as geographic expansion.

Use a two-layer discovery model. Keep the broad Smart City baseline across market activity, competitors, technology, and policy, then add a product-experience overlay. Search the overlay for observable user journeys, pain points, service interactions, accessibility, safety, adoption, and outcomes around neutral solution categories. Never let the overlay replace or narrow the Smart City baseline. Do not read or match the VSF product catalog.

Run two discovery channels for every product-experience query: one RSS channel using Bing with Google fallback, and one ordinary Web Search channel that fetches candidate source pages. The Web Search channel must run even when RSS already returns results. Apply the same date window, blocked-source rules, deduplication, source validation, content extraction, translation gate, and Gate 1 boundary to both channels. Reject undated Web Search pages rather than guessing their publication date.

## Enforce the pipeline boundary

Read `C:\WR3\AGENTS.md` before every run. Do not skip a News stage or bypass Gate 1. Never approve a HITL decision.

Treat product-adjacent discovery only as generic query expansion. Do not read, import, copy, hash, compare, or filter against `.agents/skills/10-product-gap/references/products.json`; Product Gap remains the only stage allowed to read and compare that catalog. Do not add portfolio linkage, product names, fit/gap judgments, scores, recommendations, Signals, or O/T labels to crawl output.

If the user asks only to create, edit, validate, or explain this skill, do not start a network crawl.

## Center discovery on user experience

Use the four neutral focus lanes defined in [discovery scope](references/discovery-scope.md):

1. smart venues, stadiums, and arenas;
2. amusement/theme parks, resorts, and visitor attractions;
3. urban or venue Digital Twins;
4. AI-enabled urban operations, security, and safety.

Across all four lanes, search from the citizen or visitor journey rather than from technology alone. Include residents using Smart City applications and urban services; drivers searching, reserving, entering, paying for, and exiting smart parking; visitors planning and navigating amusement or theme parks; and fans arriving at, entering, moving through, purchasing at, staying safe in, and leaving stadiums or arenas.

Also run the cross-cutting place-experience overlay for public-facing urban interfaces. Treat roadside LED displays, digital billboards, public-information screens, and wayfinding as user-experience and safety evidence when a source documents visual comfort, glare, distraction, cognitive load, accessibility, pedestrian/driver safety, complaints, enforcement, mitigation, or measured outcomes. This overlay applies to pedestrians, drivers, residents, visitors, and operators; advertising announcements alone remain out of scope.

For Vietnam, always run dedicated Vietnamese-locale place-experience queries. Cover natural-language harm and response vocabulary, including màn hình LED, biển quảng cáo điện tử, người đi đường, người đi bộ, người lái xe, chói mắt, tấn công thị giác, mất tập trung, an toàn giao thông, phản ánh, xử lý, khắc phục, and giới hạn độ sáng. Do not rely on translated English queries to discover Vietnamese user-experience reporting.

For the first two lanes, expand the whole journey: discovery and planning; travel and arrival; parking or transit; identity, ticketing, and entry; navigation and accessibility; queueing; service and commerce; real-time engagement; safety and incident handling; exit; and post-visit feedback or loyalty. Do not reduce experience reporting to a list of installed technologies.

For Digital Twins and urban AI, connect capability evidence to an actual human or operator workflow: who uses it, at which decision point, with what data or interface, under which operational condition, and with which measured or reported outcome. Keep the description neutral and source-grounded.

Prefer official demonstrations, operator walkthroughs, user-journey clips, deployment case studies, procurement/project-owner pages, post-deployment reviews, and reputable reporting. A clip is usable evidence only when its publisher, URL, publication date, and source description, captions, transcript, or accompanying article are auditable. Never infer unseen steps or outcomes from visuals alone.

Treat URLs explicitly supplied by the user as priority discovery seeds, not as automatic KEEP decisions. Attempt direct retrieval and normal source validation. If a supplied URL is within the requested date window and is not blocked but RSS and direct extraction both fail, preserve it as a `METADATA_ONLY` Gate 1 candidate using only source-grounded URL/title/date metadata; record the retrieval failure and require the reviewer to open the source. Never invent article facts from the slug or title.

Reject blocked or disinformation sources before candidate retention. Treat `电玩巴士` and the `tgbus.com` domain as blocked sources: do not retain, translate, summarize, or send their records to Gate 1. Report blocked-source counts in the crawl audit. A blocked-source record cannot be restored merely because another query or provider discovers the same syndicated item.

Treat named venues, brands, and cities as rotating discovery seeds, not permanent filters. A full crawl must retain broad global discovery and must not become anchored to the examples from one prior week.

Keep baseline Smart City queries for urban mobility, public safety, city/IOC platforms, AI/AIoT and IoT, data and Digital Twins, environment, utilities, infrastructure, governance, procurement, and emerging capabilities. A candidate outside the four focus lanes remains eligible for Gate 1 when it has concrete Smart City evidence.

## Prepare the run

Read [discovery scope](references/discovery-scope.md) before changing queries, providers, geographic coverage, or source priorities.

Run the bundled preflight first:

```powershell
python C:\WR3\.agents\skills\crawl-wr3-news\scripts\run_crawl.py --check-only
```

Require `status: PASS`. Fix missing runtime files, missing broad Smart City baseline queries, missing China/Singapore query coverage, missing catalog-independent Competitor discovery, missing product-experience focus lanes, missing citizen/parking/attraction/stadium journey queries, missing the parallel Web Search/source-fetch provider, missing dedicated Vietnamese public-space experience queries, missing journey/evidence query terms, missing blocked-source enforcement, or forbidden catalog references before crawling.

Use a rolling seven-calendar-day window including the run date in `Asia/Bangkok` unless the user specifies another end date or duration. An explicit request to crawl authorizes sending the configured queries to Google/Bing RSS and Bing Web Search, then fetching candidate source pages for date and content validation.

## Crawl and stop at Gate 1

Run:

```powershell
python C:\WR3\.agents\skills\crawl-wr3-news\scripts\run_crawl.py --days 7 --timezone Asia/Bangkok --providers bing,google,web
```

Pass `--end-date YYYY-MM-DD`, `--run-id`, `--max-items-per-stage`, `--max-competitors`, `--content-workers`, or `--min-usable-content-ratio` when needed. `--max-competitors` limits only catalog-based competitor queries; it must not disable open competitor discovery. Keep body extraction enabled for the deliverable run; use `--no-content` only for a bounded discovery or diagnostic pass.

The runner must use all four canonical News stage crawlers and then create the Gate 1 review package. Stop when the News Relevance decision is PENDING or otherwise not APPROVED. Do not continue to Signal Synthesis.

Before creating the Gate 1 package, translate every non-Vietnamese record's `title`, `summary`, `key_facts`, and `relevance_rationale` fully into Vietnamese. Preserve `original_title`, `original_language`, and original source excerpts in `crawl_evidence`, then set `translation_status: COMPLETE` and list all four fields in `translated_fields`. If the translation gate reports `PENDING`, translate the retained raw input and rerun `run_vertical_slice_01.py` with that input and the same unused run ID. Never use foreign-language text as a reviewer-facing fallback.

Do not overwrite an existing live input directory or run directory. Use a new run ID for each rerun. Preserve partial crawl evidence when providers or content extraction fail.

## Audit the result

Inspect the runner JSON and generated files under:

- `workspace/inputs/news/live/<run-id>/`
- `workspace/runs/<run-id>/artifacts/`
- `workspace/runs/<run-id>/reviews/`
- `workspace/runs/<run-id>/validation/`

Report the exact date window, counts for all four News types, RSS and Web Search attempts/results/fetch failures, content-quality status, Vietnamese translation-gate status/counts, whether China and Singapore query attempts were executed, and whether catalog-independent competitor queries covered Vietnam, China, and Singapore. Also report query attempts and retained records by each product-experience lane, plus how many retained sources contain auditable journey touchpoints, user/operator roles, deployment status, and outcomes. Distinguish provider failure, undated Web Search rejection, source-fetch failure, and a valid zero-result query.

Confirm the run stopped at News Relevance HITL and that no human decision was auto-approved. Present the output as ready for human Gate 1 review, not as evaluated market intelligence.

## Diagnose low coverage

Use query attempts, per-stage crawl audits, focus-lane coverage, journey-touchpoint evidence, content status counts, and source-resolution failures together. Diagnose a lane as shallow when results merely announce technology without identifying a user/operator workflow, journey stage, friction, or outcome. Expand one dimension at a time: context, journey stage, capability, evidence type, then geography or language. Retry a bounded run with lower concurrency or a different provider order when rate limited. Never infer that a market was quiet solely from a small result set.

Keep source URLs unchanged and preserve Chinese/English originals only in crawl evidence. Translate all reviewer-facing News fields into Vietnamese according to the WR3 review-language policy.

## Latest crawl note

- Run ID: `20260817-164000-live` (Gate 1 package generated from live crawl input `20260817-161500-live`)
- Crawl window: `2026-08-12` through `2026-08-17` inclusive in `Asia/Bangkok`
- Gate reached: News Relevance HITL
- Gate status: `PENDING`; pipeline blocked for human review
- Retained News records: 21 (`MARKET`: 4, `COMPETITOR`: 2, `TECHNOLOGY`: 11, `POLICY`: 4)
- Blocked-source result: six blocked feed items were excluded; retained records contain no blocked sources
- Provider result: 282 successful attempts and 38 failed attempts across RSS and Web Search/source fetch. Web Search ran 30 experience queries, returned 147 result links, fetched 125 source pages, rejected 115 as journey-irrelevant and six as undated, and recorded 22 page-fetch failures; no Web Search-only result met all retention checks in this window.
- Content-quality handling: body extraction ran with two workers; 5 records are `FULL_TEXT`, 16 are `METADATA_ONLY`, and the final input passed the 10% usable-content threshold at 23.81%.
- Vietnamese review translation: 13 records completed from auditable crawl evidence; 8 records did not require translation.
- Citizen and visitor experience overlay: dedicated queries covered Smart City services used by residents, smart parking, amusement/theme parks, stadiums, Digital Twins, public-space visual comfort, accessibility, queues, safety, complaints, and operational outcomes. RSS directly found the supplied Dân trí LED article, which is retained once as a POLICY candidate. Other retained journey examples include accessibility at Carleton Place Arena, Karsan autonomous passenger service at Efteling theme park, and Rancho Cordova city Digital Twin coverage.

Update this note after each completed deliverable crawl. Record explicit local start/end dates rather than only writing “last 7 days”.
