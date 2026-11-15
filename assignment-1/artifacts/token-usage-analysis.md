# Part 2: Token usage analysis

## Setup

Task: `django__django-15368`. Both independent runs used the DeepSeek official endpoint with model ID `deepseek-flash`, documented as DeepSeek-V4.1-Flash-1017 at https://api-docs.deepseek.com/ when run. This differs from the course's historical default. The API response records the alias, not an immutable version ID. Both runs used a 200-action limit, the same code and skills, and separate fresh Modal sandboxes. The compacted run used a 6000-token threshold; the baseline disabled compaction. Modal image builder `2025.06` was selected for compatibility with the locked client.

## Observed usage

Counts below come from API response `usage` fields. Summary overhead includes both summary input and output tokens; it is included in the combined total.

| Condition | Action calls | Action input tokens | Action output tokens | Summary total tokens | Combined total tokens | Peak action input tokens |
|---|---:|---:|---:|---:|---:|---:|
| Compaction (6000) | 17 | 71,047 | 2,550 | 18,979 | 92,576 | 5,725 |
| Full context (0) | 22 | 195,716 | 4,347 | 0 | 200,063 | 14,167 |

The compacted run made four additional model calls for summaries (16,667 input and 2,312 output tokens). Combined input was 87,714 tokens. Including this overhead, total token use was **53.7% lower** in this sample. The baseline made no summary calls.

## Compaction evidence

| After action | Estimated active tokens before | Estimated active tokens after | Reduction |
|---|---:|---:|---:|
| 2 | 5,550 | 2,225 | 59.9% |
| 5 | 5,348 | 2,538 | 52.5% |
| 7 | 5,766 | 2,475 | 57.1% |
| 11 | 5,406 | 1,718 | 68.2% |

These event counts use the harness's character-based estimator. The trigger uses a separate estimate calibrated by the preceding API usage; therefore the logged before-count can be below 6000 even though the trigger fired. Original system and task messages remain verbatim, with the latest assistant action and all linked tool observations retained. Summary text replaces only the old prefix.

## Interpretation and tradeoffs

Compaction reduces the amount of old tool output resent on later requests and caps active context. It adds summary-generation cost and can omit details, causing repeated investigation. Here the compacted run also finished in fewer actions (17 versus 22), so the total difference reflects different stochastic trajectories as well as compression. A single pair of runs does not establish a universal savings rate or speed advantage.

Token savings are not the same as billing savings. Including summaries, the compacted run reported 55,168 cache-hit input tokens and 32,546 cache-miss input tokens; the baseline reported 184,960 cache-hit and 10,756 cache-miss input tokens. Summarization changes prompt prefixes and reduces cache reuse. Actual charges depend on provider rates for cache hits, misses and outputs; no dollar-cost claim is made here.

The compacted patch passed fresh-sandbox replay: FAIL_TO_PASS 1/1 and PASS_TO_PASS 29/29. See `part2-evaluation.log`. Baseline replay is recorded separately in `part2-baseline-evaluation.log`.

## Evidence

- `django__django-15368-trajectory.json` and `.patch`: compacted run.
- `django__django-15368-baseline-trajectory.json` and `.patch`: baseline.
- `part2-evaluation.log` and `part2-baseline-evaluation.log`: independent patch replay results.
