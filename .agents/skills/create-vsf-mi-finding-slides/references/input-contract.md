# Input contract

The generator accepts validated UTF-8 fine-tuned Markdown produced by the `writing-style` handoff from `summarize-mi-run`, with exactly these sections:

```text
# Market Intelligence Report
run metadata
## 1. Executive Summary
### SIGNAL-... → ACTION-...
## 2. Findings
### SIGNAL-... — title
#### News
#### Opportunity / Threat
#### Product Mapping
#### Product Gap
#### Action
## 3. Approach
### Từ Signal đến Action
### Cách đọc hướng phản hồi
```

## Parsing and validation

- Read `Run ID`, `Thời gian`, and `Crawl 1 tuần` from metadata below the H1.
- Require one Executive Summary H3 block per Finding with exactly one Signal and one Action.
- Within each Finding, keep the leading Signal fields and each H4 subsection attached to that Signal.
- Parse every bold `NEWS-` record, its required `Liên hệ SIGNAL-…` sentence, full summary, source name, and exact source URL.
- Require the connection line immediately after the News title and before its summary. Its Signal ID must equal the containing Finding Signal ID, and its explanation must be non-empty and no longer than 180 characters.
- Retain all O/T, Map, Gap, and Action fields and nested bullets without rewriting or shortening them.
- Accept the fine-tuned display aliases `Trạng thái năng lực` for `Trạng thái capability` and `Năng lực còn thiếu` or `Tính năng còn thiếu` for `Capability còn thiếu`; preserve their values and lineage exactly.
- Require exactly one Product Mapping, one Product Gap, and one approved Action per Finding.
- Validate O/T to Signal, Gap to Product Mapping, and Action to Gap using exact IDs. Never infer joins from similar wording.
- Split `Capability còn thiếu` at semicolons into complete display items; do not shorten the items. Render one table row per item and leave its paired `THAM CHIẾU` cell blank for the user to fill in PowerPoint.
- Preserve source order, IDs, enums, and URLs. Strip Markdown presentation characters only.

## Slide mapping

| Markdown layer | HTML slide treatment |
| --- | --- |
| H1 + metadata | Cover |
| Executive Summary | One full Signal-to-Action row per H3, plus a blank `Công nghệ đã kiểm chứng:` fill-in placeholder |
| Each Findings H3 | Three consecutive Finding-board pages: Evidence/O-T, blank real-world reference template, then Mapping/Gap/Action |
| Approach | One methodology and response-enum slide |

The middle Finding page is presentation scaffolding, not a new pipeline stage or analytical record. Do not read, infer, or copy technology examples into its placeholders. Require exactly the three numbered Markdown sections and fail clearly on missing sections, broken lineage, missing source images, or non-bijective Executive Summary mappings. Expected count: `3 + 3 * number_of_signals`.

## Optional source-deck overlay

Accept an explicitly supplied approved HTML deck through `--source-deck`. Extract only:

- News ID and Signal lineage from each Finding News slide;
- the visible News H4 article title and direct `dd/mm/yyyy` date in the footer beside the source link (accept the legacy `Xuất bản: dd/mm/yyyy` form when reading an older overlay);
- the original article title from the H4 `title` attribute for exact matching;
- one to three exact `<mark class="mi-news-highlight">` phrases per News summary.

Cross-check every News ID, Signal ID, article title, Signal connection, and highlighted phrase against the Markdown. The overlay may contain the legacy `Liên hệ SIGNAL-ID:` prefix or only the explanation; the Markdown connection is authoritative, and an overlay whose visible explanation differs must be rejected. Never import O/T, Map, Gap, Action, IDs, enums, source URLs, or analysis wording from the HTML overlay.
