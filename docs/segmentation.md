# Firm segmentation: the method

How this project decides what a firm *is*, why it uses five axes instead of one
category list, and the rules it uses to separate firms that look alike.

- Labels and rules: [`taxonomy.yml`](../taxonomy.yml)
- Prompting, validation, rendering: [`src/firm_analyzer/core/segmentation.py`](../src/firm_analyzer/core/segmentation.py)
- Per-firm output: `firm_results/<category>/<firm>/segmentation.json`, a
  `## 세분류` table in `summary.md`, and flat columns in `<category>_firms.csv`

## Why the flat category list wasn't enough

The original scheme had four buckets — `finance`, `healthcare`, `ai_ml`,
`general` — and most firms landed in `general`. The deeper problem is that a
single label has to answer several unrelated questions at once. Take a fabless
AI-accelerator startup:

| Question | Answer |
| --- | --- |
| What industry is it in? | Semiconductors |
| What technology does it build on? | AI/ML, chip design |
| How does it earn revenue? | Selling components to device makers |
| Where does it sit in the chain? | Component supplier, not a finished product |
| What would a 전문연구요원 actually do there? | Applied development |

Forcing that into one slot means picking one fact and discarding four. Both
`semiconductor` and `ai_ml` are defensible, which is exactly why a flat list
produces arbitrary-feeling results.

The established taxonomies split the same way. KSIC and NAICS classify a
production unit by its **principal activity**; GICS classifies by **principal
business activity** and revenue source; Crunchbase and PitchBook keep
technology **verticals** as a separate, multi-label dimension precisely because
they cross-cut industry. Standard taxonomies are also *hierarchical*, not flat:
KSIC's 11th revision runs 21 sections → 77 divisions → 234 groups → 501 classes
→ 1,205 subclasses, and GICS runs 11 sectors → 25 industry groups → 74
industries → 163 sub-industries.

## The five axes

| Axis | Cardinality | Answers |
| --- | --- | --- |
| `sector` → `subsector` | one label, two levels | What the firm mainly does |
| `verticals` | 0–3 labels | Which technologies it builds and sells |
| `business_model` | one label | How it earns revenue |
| `value_chain` | one label | Where it sits between raw research and end user |
| `profile` | three enums | Size tier, R&D intensity, likely research role |

10 sectors, 45 subsectors and 20 verticals — deliberately smaller than KSIC.
The list covers what actually appears in the 전문연구요원 배정 list, and every
label has to be decidable from a handful of search results. A taxonomy that is
too fine for the available evidence just moves the arbitrariness from the label
to the guess.

Each firm also carries per-axis `confidence` (high/medium/low), an `evidence`
sentence per axis (with a source URL where possible), and the `signals` — the
keywords that drove the decision. That is what makes a result auditable
instead of a verdict: you can see *why*, and low confidence is a visible,
filterable state rather than a silent one.

The coarse `categories` in `config.yml` still exist and still decide the output
directory; each sector maps onto one via `legacy_category` in `taxonomy.yml`, so
existing paths and the dashboard keep working.

## How firms that look alike get separated

The hard cases are almost never "which sector is this" — they are "which of two
adjacent sectors", and the answer is usually a **revenue-model** question, not
a topical one. These rules live in `taxonomy.yml` and are injected verbatim into
the classification prompt.

**Principal-activity rule (from KSIC).** A firm that does several things is
classified by the activity with the largest **value added**; if that is unknown,
by revenue; if that is unknown, by headcount. Applied consistently, this settles
most conglomerate and side-business cases.

**Revenue source over self-description.** "AI 기반", "종합 솔루션" and
"플랫폼" are marketing copy. The question is always *who pays for what*.

| Looks the same | Distinguished by |
| --- | --- |
| Product vendor vs SI/용역 | One product licensed to many customers → product. Per-customer projects billed by man-month → SI. |
| An AI company vs a company using AI | Is the model the thing being sold, or an internal efficiency tool? Only the former earns an AI vertical. |
| Fabless vs foundry vs equipment | Owns design IP and outsources fabrication → fabless. Fabricates others' designs → foundry. Builds the process machines → equipment. |
| Materials vs components | Sold as a compound, powder or raw input → materials. Sold as a functioning part or module → components. |
| Drug developer vs CRO/CDMO | Owns the pipeline and indication → developer. Runs others' molecules through development, manufacturing or assay → CRO/CDMO. |
| Marketplace vs distributor | Takes inventory and sells at a margin → distribution. Brokers third-party transactions for a fee → platform. |
| Research institute vs company | Funded mainly by government appropriations with no product revenue → institute. Product or service revenue dominant → its industry sector. |
| Holding company | Classified by the operating business it actually runs; no operating substance → `other`. |

**Verticals are additive, not competing.** A fabless firm is
`semiconductor_hardware` *and* `chip_design` — the axes are orthogonal by
design, so the earlier "semiconductor or AI?" dilemma disappears.

**No evidence means `unknown`.** An admitted gap is more useful than a
confident guess, and it is the only outcome that can be reviewed later.

### Validated against boundary cases

Run on firms picked to sit exactly on those boundaries (Gemini
`gemini-3.1-flash-lite`):

| Firm | sector / subsector | verticals | business model | value chain |
| --- | --- | --- | --- | --- |
| 텔레칩스 | semiconductor_hardware / fabless_design | chip_design, embedded_firmware | component_supplier | parts |
| LG CNS | ict_software / it_service_si | ai_ml, data_engineering, cloud_devops | b2b_solution | system_integration |
| 알테오젠 | bio_health / drug_discovery | bioinformatics | licensing_ip | basic_research |
| 엘앤에프 | chem_materials_energy / battery_storage | advanced_materials | component_supplier | materials |
| 넥슨코리아 | ict_software / game | ai_ml, data_engineering, xr_graphics | b2c_service | service_operation |
| 채널코퍼레이션 | ict_software / app_platform_sw | ai_ml, genai_llm, nlp_speech | b2b_saas | service_operation |

All six separate the way the rules intend — note especially 알테오젠 landing on
`licensing_ip` (its revenue is technology-transfer milestones and royalties, not
product sales) and 엘앤에프 on `materials` rather than `parts` (cathode material,
not a component).

## Implementation notes

**One call, whole taxonomy.** Summary and segmentation come from the same
request, and the entire taxonomy goes into the prompt rather than walking the
hierarchy level by level. Path traversal costs one call per level and loses
cross-axis consistency — the model can no longer notice that "fabless" in the
subsector implies chip design on the vertical axis. Research on hierarchical
classification with LLMs finds single-pass and path-traversal variants both
workable; single-pass wins here because the taxonomy fits comfortably in one
prompt.

**Validation is mandatory.** `validate_segmentation()` checks every label
against `taxonomy.yml`: unknown ids become `unknown`, a subsector belonging to a
different sector is dropped, verticals are de-duplicated and capped at three,
and scalar answers where the contract says list/object are coerced. Malformed
output degrades to a low-confidence record instead of raising, so one odd firm
cannot abort a run of several hundred. A hallucinated category that reaches a
CSV column is worse than an admitted gap.

**Keywords earn their place in the prompt.** Each sector and subsector carries
Korean keywords, which anchor industry terms a model may otherwise read
loosely (소부장, 팹리스, 출연연).

## Extending the taxonomy

`taxonomy.yml` is data — edit it without touching code:

- **New subsector**: add it under its sector with keywords. Ids must be globally
  unique (a test enforces this) because they appear in flat CSV columns.
- **New sector**: add it with a `legacy_category` so firms still get an output
  directory, plus `distinguish` rules for whatever it will be confused with.
- **New vertical**: add it to `verticals`. Raise `max_verticals` if three is too
  tight.
- **New tie-break rule**: add to a sector's `distinguish` list (local) or to the
  top-level `rules` (global). Both are injected into the prompt verbatim.

Turn the whole thing off with `segmentation.enabled: false` in `config.yml`, or
`--no-segmentation` on `scripts/run_summarize.py`.

## Segmenting firms that were already summarized

summarize segments only the firms it processes, and it skips any firm whose
folder already exists. Firms summarized before the taxonomy existed, or before
an edit to it, are re-classified with `scripts/run_segment.py`
(`firm-segment`). It sends the standalone segmentation prompt
(`build_segmentation_prompt`) over each folder's saved `raw_search.json`, so it
costs one model call per firm and no searches, and it runs the result through
the same `validate_segmentation()`.

- Default: firms without `segmentation.json`. `--force` re-does the rest too.
- The `## 세분류` table goes between the summary.md header and its body. With
  `--force` the old table is replaced only if it matches the previous
  `segmentation.json` exactly; a hand-edited table is left alone and reported.
- `--relocate` moves each folder to the sector's `legacy_category` and updates
  the `**Category:**` line. It never overwrites an existing folder.
- Per-firm failures are skipped and listed; a rate-limit or quota error stops
  the run. Re-running picks up where it stopped.
- The `<category>_firms.csv` files are not rewritten. Use `firm-export` for a
  CSV that includes every firm's segmentation columns.

## Sources

Taxonomy design follows established practice; the tie-break rules and the
Korean label set are specific to this project.

- [한국표준산업분류(KSIC) 제11차 개정 고시 — 국가데이터처](https://mods.go.kr/board.es?mid=a10403040000&bid=107&act=view&list_no=428660)
- [한국표준산업분류 소개: 생산단위의 주된 산업활동 기준 — 통계분류포털](http://kssc.kostat.go.kr/ksscNew_web/kssc/common/selectIntroduce.do?gubun=1&bbsId=ksic_s&categoryNameCode=001&categoryMenu=003)
- [KSIC 제11차 개정 분류체계 변화 (대·중·소·세·세세분류 항목 수)](https://mods.go.kr/boardDownload.es?bid=108&list_no=422598&seq=2)
- [The Global Industry Classification Standard (GICS) — MSCI](https://www.msci.com/indexes/index-resources/gics)
- [Global Industry Classification Standard — Wikipedia](https://en.wikipedia.org/wiki/Global_Industry_Classification_Standard)
- [North American Industry Classification System — Wikipedia](https://en.wikipedia.org/wiki/North_American_Industry_Classification_System)
- [What Are GICS Codes? GICS sectors and structure — SICCODE](https://siccode.com/page/what-is-a-gics-code)
- [Industry Classification (GICS vs NAICS vs SIC) — University of St. Thomas](https://libguides.stthomas.edu/industry/industry_classification)
- [PitchBook vs Crunchbase: taxonomy granularity and verticals — Exploding Topics](https://explodingtopics.com/blog/pitchbook-vs-crunchbase)
- [Single-pass Hierarchical Text Classification with Large Language Models](https://payberah.github.io/files/download/papers/llm_classification.pdf)
- [LLM-as-classifier: a semi-supervised, iterative framework (arXiv 2508.16478)](https://arxiv.org/pdf/2508.16478)
