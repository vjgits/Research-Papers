# PGER V9.3 frozen two-stage semantic evidence search — bounded open-weight comparison

**Frozen October 28, 2026 UTC.** Isolated branch `v93-semantic-two-stage-2026-10-28`, main unchanged. No paid APIs, cron, reviewer agents, or autonomous indefinite jobs. **These are pretrained prior-art components, not an independently novel PGER algorithm.**

## Why and specific hypothesis
V9.2 lexical phrase expansion failed confirmation. SAG2's strong results partly arise from semantic decisions about **necessary intermediate evidence**, not just repeated search. Existing V8.3 showed generic MS MARCO cross-encoder improves MuSiQue but is CPU-expensive. Test whether using semantic scoring to *choose expansion seeds* and re-scoring the next 32 new candidates can improve source-chain recovery compared with spending the same 64 cross-encoder comparisons solely on V7.1's initial documents.

## Freeze datasets and inference budget
- Exact original pinned SAG2/HippoRAG2 full passage corpora and question IDs, checked by official adapter (`v7-multihop/benchmark_v71_sag2_official.py`).
- MuSiQue and 2Wiki: **first 40 questions each** development, **next 120** per dataset unchanged-confirmation. These are public datasets already repeatedly studied, **not sealed independent test**.
- Baseline: unchanged original V7.1 graph, zero model calls. CE64 control: the first 64 unique fast/BM25 passages each scored once with `cross-encoder/ms-marco-MiniLM-L6-v2`.
- Two-stage arm: same first **32** passages are scored, then the top-3 CE-ranked sources seed up to eight independently sourced BM25 term searches. Rank-fusion proposes **32 new source passages**, each scored once by the identical model. That is **64 cross-encoder passage evaluations per arm**, although both arms make a different number of BM25 calls and the scoring paths have different passage length distributions. Keep first two original fast sources or do not protect them; all four arms frozen.
- Shared initial 32 CE predictions reused *within the experiment*; actual CPU stage timing for first32/fast-tail32/rescue-tail32 recorded separately. Do not claim results are deployed single-path timings.
- CPU-only 2 threads, batch=24, max_length=224, first 1050 chars plus title. No fine-tuning, no paid API. HuggingFace revision not pinned in this first pilot; inspect and pin for future replication.

## Metrics and gates
- Complete annotated evidence set @5/@10, average per-source recall, 2/3/4-support breakdown, candidate oracle full-chain coverage@64 (post hoc only), paired 3000-bootstrap question CI, wins/losses, source witness queries and CPU costs.
- Keep model and query selection fixed between dev and confirmation. Any gain must exceed V7.1 baseline AND same-budget CE64 comparator at useful accuracy-cost frontier; more searches cannot count as more efficient without cost.
- No generated answers, human evidence entailment, contradictions/abstentions, official independent SAG2 JEV rerun, 5+/8-hop claims.
- If 4-source MuSiQue remains 0 at Top5 and gain is small, abandon this heuristic and prioritize a stronger open-weight *necessary evidence* scorer and independent benchmark; don't tune on confirmation data.

## Commands
```bash
python -m unittest discover -s . -p 'test_v93.py' -v
python benchmark_v93.py smoke
python -u benchmark_v93.py run --datasets musique 2wikimultihopqa --start 0 --limit 40 --out results-v93
python -u benchmark_v93.py run --datasets musique 2wikimultihopqa --start 40 --limit 120 --out results-v93
```
