# WR3 crawl discovery scope

## Geographic coverage

Every full crawl must attempt Vietnam, global, China, and Singapore queries.

Competitor discovery is not limited to companies already listed in `competitors.json`. This rule broadens company discovery, not geographic coverage. Within the configured Vietnam, China, and Singapore competitor queries, every full crawl must combine:

- catalog-based queries for known competitors; and
- open, capability/activity-based queries for emerging or previously unknown competitors in Vietnam, China, and Singapore.

Treat `competitors.json` as a read-only recognition and known-entity tracking source, not a whitelist. Keep a candidate from an uncataloged company when it contains concrete competitive activity or positioning; Gate 1 decides final relevance.

For China, use both Simplified Chinese and English discovery variants. Prefer official national or municipal portals, standards and cybersecurity authorities, procurement/project-owner pages, company newsrooms, and reputable publications. Search terms should cover `智慧城市`, `城市大脑`, `数字城市`, `人工智能`, `物联网`, `数字孪生`, `计算机视觉`, `智能交通`, project, procurement, deployment, tender, policy, standard, and data governance.

For Singapore, use English variants containing `Singapore`, `Smart Nation`, or `smart city`. Prefer government, regulator, transport/urban-planning authority, public procurement, project-owner, company newsroom, and reputable publication sources. Search terms should cover tender, procurement, pilot, deployment, regulation, standard, digital twin, IoT, video analytics, intelligent transport, and environmental monitoring.

Use locale-aware provider requests:

| Geography | Google News | Bing News |
| --- | --- | --- |
| Vietnam | `VN:vi` | `vi-VN` |
| China | `CN:zh-Hans` | `zh-CN` |
| Singapore | `SG:en` | `en-SG` |
| Global | `US:en` | `en-US` |

RSS is discovery evidence, not the final source of truth. Run a Web Search/source-fetch channel in parallel for every product-experience query, even when RSS returns candidates. Prefer resolved direct article URLs and extracted source-page content. Apply the configured date window to source-page publication metadata; reject undated Web Search pages instead of inferring freshness from search rank.

When the user supplies an example article URL, treat it as a priority seed in addition to query expansion. Try direct retrieval, validate the date window and blocked-source rules, and deduplicate it against provider results. If retrieval is blocked but the URL, publisher, title, and date are source-grounded and in-window, retain a `METADATA_ONLY` record for Gate 1 with the retrieval failure stated explicitly. User supply does not constitute a KEEP decision and does not authorize invented facts.

## Blocked sources

Exclude the following at ingestion, before deduplication, classification, translation, and Gate 1 packaging:

- source label `电玩巴士`;
- domain `tgbus.com` and its subdomains.

Record the number of blocked feed items per query/provider and in the stage crawl audit. Do not use blocked-source text to enrich another retained record. If a different reputable publisher independently reports the same underlying event, assess that publisher's article on its own evidence.

## Two-layer coverage model

Every full crawl must run both layers:

1. **Smart City baseline:** broad Market, Competitor, Technology, and Policy discovery across Vietnam, global, China, and Singapore. Cover urban mobility, public safety, city and IOC platforms, AI/AIoT, IoT and edge, urban data, Digital Twins, environment, energy and lighting, utilities, infrastructure, governance, procurement, standards, privacy, and cybersecurity.
2. **Product-experience overlay:** the four focus lanes and journey-first queries below.

Do not use the overlay to filter baseline candidates. News outside the focus lanes remains eligible for Gate 1 when it provides concrete Smart City market, competitor, technology, or policy evidence. Conversely, venue or attraction lifestyle content without a technology, operating-model, deployment, procurement, policy, or measurable service-experience dimension is not made relevant merely by matching the overlay vocabulary.

## Product-experience discovery taxonomy

Use the following user-approved neutral focus lanes. They are search scope, not a copy or interpretation of the VSF portfolio catalog.

### Smart venues, stadiums, and arenas

Search from the fan, visitor, staff, and operator perspectives across the complete event journey:

- discovery, planning, ticket purchase, identity, and mobile wallet;
- trip planning, transit, parking, arrival, security screening, and entry;
- wayfinding, accessibility, seating, crowd flow, and queue management;
- concessions, retail, cashless payment, connectivity, content, and real-time engagement;
- safety, incident response, evacuation, exit, post-event feedback, and loyalty.

Useful capability seeds include mobile ticketing, digital identity, frictionless or biometric entry, smart parking, indoor navigation, digital signage, high-density connectivity, queue and crowd analytics, computer vision, cashless commerce, personalization, accessibility technology, command center, and venue Digital Twin.

### Amusement/theme parks, resorts, and visitor attractions

Search the guest journey before, during, and after a visit. Cover trip planning, booking, arrival, admission, itinerary and navigation, virtual or physical queues, accessibility, attraction availability, staff interaction, food and retail, immersive or personalized experiences, safety, lost-child or incident handling, exit, feedback, and return visits.

Useful capability seeds include guest apps, wearables, digital passes, reservation and virtual-queue systems, indoor/outdoor navigation, location services, demand and crowd forecasting, personalized itineraries, immersive media, robotics, computer vision, cashless commerce, accessibility, and attraction or resort Digital Twins.

### Urban and venue Digital Twins

Search beyond generic platform announcements. Require an identifiable workflow such as planning, simulation, asset or facility operations, mobility, event operations, environmental monitoring, emergency response, public consultation, or frontline decision support. Capture the user/operator role, data sources, interface or visualization, update cadence, interoperability, decision supported, maturity, and reported outcome.

Useful capability seeds include 3D/4D city models, geospatial platforms, BIM/GIS integration, real-time IoT synchronization, scenario simulation, predictive maintenance, crowd or traffic simulation, operational dashboards, open standards, APIs, and immersive visualization.

### AI-enabled urban operations, security, and safety

Search for concrete AI-assisted workflows in public safety, traffic and crowd operations, abnormal-event detection, emergency response, infrastructure inspection, environmental operations, citizen service, and operations centers. Capture the human-in-the-loop role, decision latency, false-positive or accuracy evidence, privacy and governance controls, deployment scale, and operational outcome. Do not treat generic AI marketing as deployment proof.

Keep the existing broad Smart City capability families—transport, parking, video analytics, computer vision, IoT/AIoT, edge, urban operations platforms, lighting, energy, environmental monitoring, industrial parks, and utilities—as the baseline rather than treating them as optional secondary terms.

These terms are search seeds only. They must not be described as existing VSF products, used to claim portfolio relevance, or populated as a portfolio field. Never read the portfolio catalog to expand, rank, accept, or reject News.

### Citizen use of Smart City services

Search for residents actually using public-facing Smart City services, not only municipal platform announcements. Cover discovery and onboarding, identity and consent, service requests, issue reporting, status tracking, notifications, payments, mobility, accessibility, support, resolution, feedback, and trust. Capture the service used, resident task, channel or interface, friction, response workflow, adoption or usage evidence, and reported outcome.

### Smart parking user journey

Search the complete driver journey: finding availability, comparing or reserving a space, approaching the facility, entry and identification, guidance to a bay, accessibility and safety, payment, EV charging where relevant, exit, receipt, dispute handling, and feedback. Look for wait time, search time, failed payment, confusing guidance, occupancy accuracy, accessibility, enforcement, and integration with public transport or city applications.

## Journey-first query construction

Build focused queries from at least three dimensions:

`experience context × journey/workflow stage × capability or friction × evidence signal`

Use evidence signals such as `walkthrough`, `video`, `demonstration`, `case study`, `pilot`, `deployment`, `post-deployment`, `user feedback`, `adoption`, `wait time`, `throughput`, `accessibility`, `satisfaction`, `incident response`, `measured outcome`, and equivalent local-language terms.

Use named venues, parks, operators, vendors, and cities only as rotating benchmark seeds. Do not let one brand, city, or prior News set dominate a full crawl. For each focus lane, retain at least one broad query independent of named entities.

Prefer sources that expose enough evidence to reconstruct:

1. user or operator role;
2. journey stage or operational decision;
3. pain point, task, or constraint;
4. capability and interaction mechanism;
5. deployment status and scale;
6. qualitative or quantitative outcome;
7. limitations, accessibility, privacy, or safety implications.

A record may still proceed to Gate 1 with missing dimensions, but missing evidence must remain explicit. Video pages without auditable captions, transcript, description, or accompanying text stay `METADATA_ONLY`; do not claim what the clip visually appears to show.

## Stage coverage

- Market: procurement, investment, buyer activity, pilots, contracts, adoption, deployments, experience metrics, and post-deployment user/operator evidence.
- Competitor: each active known competitor's existing queries, together with catalog-independent open discovery for companies in Vietnam, China, Singapore, and broad unnamed-entity product-experience lanes. A company absent from `competitors.json` remains eligible for Gate 1 `KEEP`; `--max-competitors` limits only catalog-based queries and must not disable open discovery.
- Technology: capability, interaction design, integration, maturity, accessibility, standards, pilots, deployments, and measured workflow outcomes.
- Policy: regulation, standards, government programs, procurement rules, data governance, privacy, cybersecurity, accessibility, biometric use, and AI accountability where they affect the focus journeys.

Deduplicate published articles conservatively across query variants. Keep the query ID and geography that discovered each retained record in crawl evidence.

## Cross-cutting place-experience overlay

In addition to the four core lanes, run a cross-cutting place-experience overlay for public spaces, amusement and visitor attractions, and smart parking. Follow the user journey from approach and arrival through navigation, waiting, service use, safety, and exit. Include pedestrians, visitors, drivers, residents, and operators.

For public-space interfaces, cover digital signage, LED displays, electronic billboards, public-information screens, and wayfinding. Capture visual comfort, glare, visual overload or cognitive load, distraction, accessibility, pedestrian/driver safety, information clarity, complaints, mitigation, enforcement, regulation, and outcomes. Use both deployment and harm/response terms (for example: visual impact, eyestrain, distracting display, roadside safety, resident complaint, brightness limit, screen-off time, and remediation) so the crawl does not only find technology-launch announcements. Do not retain advertising content by itself as Smart City evidence.

Run dedicated Vietnamese-locale variants for this public-space interface scope. Include natural Vietnamese combinations such as `màn hình LED`, `biển quảng cáo điện tử`, `màn hình công cộng`, `người đi đường`, `người đi bộ`, `người lái xe`, `chói mắt`, `tấn công thị giác`, `mất tập trung`, `an toàn giao thông`, `phản ánh`, `khiếu nại`, `xử lý`, `khắc phục`, and `giới hạn độ sáng`. Treat these as discovery seeds rather than a closed vocabulary. Retain reputable reporting about documented harm, complaints, regulatory response, or mitigation even when it is not a technology-launch article.

For parking, cover search and reservation, approach, entry, guidance, payment, accessibility, safety, exit, and feedback. Use neutral seeds such as smart parking, parking guidance, occupancy, payment, EV charging, curb management, accessibility, wait time, and incident response. Retain only records that show a technology, operating model, deployment, policy, or measurable service-experience dimension.
