# Pipeline Version

- Version: 1.0.0-contract
- Status: FROZEN_FOR_IMPLEMENTATION
- Scope: Pipeline contracts, schemas, HITL templates and dependency rules
- Runtime logic: Not implemented
- Market Intelligence run: Not executed

## Skills

1. 00-news-driven-mi-orchestrator
2. 01-market-news
3. 02-competitor-news
4. 03-technology-news
5. 04-policy-news
6. 05-news-relevance-hitl
7. 06-signal-synthesis
8. 07-opportunity-threat
9. 08-opportunity-threat-hitl
10. 09-product-mapping
11. 10-product-gap
12. 11-action-recommendation
13. 12-product-action-hitl
14. 13-mi-quality-control

## HITL Gates

1. News Relevance HITL
2. Opportunity / Threat HITL
3. Product Action HITL

## Canonical pipeline

Market News + Competitor News + Technology News + Policy News
→ News Relevance HITL
→ Signal Synthesis
→ Opportunity / Threat
→ Opportunity / Threat HITL
→ Product Mapping
→ Product Gap
→ Action Recommendation
→ Product Action HITL
→ Quality Control

## Reference catalogs

- Competitors: `.agents/skills/02-competitor-news/references/competitors.json`
- Products: `.agents/skills/10-product-gap/references/products.json`

## Frozen invariants

- Product Mapping does not read products.json.
- Only Product Gap reads products.json.
- Only Competitor News reads competitors.json.
- No HITL gate may be bypassed.
- No AI or orchestrator auto-approval.
- Only KEEP news feeds Signal.
- Only APPROVE O/T feeds Product Mapping and Action.
- Only APPROVE actions are final; DEFER is backlog.
- ID lineage is `news_id → signal_id → ot_id → product_mapping_id → gap_id → action_id`.

## Known implementation obligations

- Build runtime semantic checks for HITL set union/disjoint invariants.
- Keep Gate 2 merge/split lineage in Markdown for v1; machine-readable replacement mapping requires an explicit future contract decision.
