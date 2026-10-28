# V17: Reproduce original SAG2 with the historical JEV provider

**Status:** Live provider calls NOT executed; zero-cost preflight validates 120 HoVer claims and source archive. This is an opt-in paid experiment, NEVER launch unattended.

## Original method

Official author repo: https://github.com/Zleap-AI/SAG-Benchmark
Pinned source commit: `bb7f82751ba1576219f9d9ebd021128603d130c3`.

SAG2 original `CorpusIndex` / `JevClient` / `search_sag2` with:
- OpenRouter POST https://openrouter.ai/api/alpha/decisions
- Request model `typesafe/jev-1.13`, historical provider response `typesafe/jev-1.13-20260917`. Hard reject any different model build.
- JEV `noul` question type, exact author's instructions and candidate/context format.
- `candidate_k=100`; `seed_k=10`; `max_hops=2`; `expansion_term_limit=20`; original author SQLite FTS5, BM25, evidence expansion and DPP.
- No synthetic scorer, no proxy and no local Qwen substitution.

OpenRouter currently lists Jev 1.13 at $0.042/1M input tokens, zero output-token charge. Its original published MuSiQue 1,000-question experiment cost ~USD 4.33, but fresh HoVer charges depend on actual prompt lengths, retries and requests. For our 120 claims, rough proportional expectation ~USD 0.52 is NOT a quote or hard bound. Use the provider's usage.cost when present, log token counts/model ID; budget gate stops new claims once cumulative spend crosses cap but an in-flight question may overshoot. Never supply a paid key over chat, hardcode it, save in .env to Git, or include in run artifacts.

## Current V17 HoVer evaluation vs original SAG2 paper

This is a new dataset, so it is NOT byte-identical to the paper's MuSiQue evaluation. Our shared HoVer pool has 16,579 original Wikipedia articles, 120 hash-selected claims (40 each at annotated 2,3,4 hops). It was constructed without gold source labels but uses the initial DRQA result lists of those same claims (transductive); it is NOT full Wikipedia. The fully required evidence corpus-availability ceilings are 30/40, 22/40, 10/40. All absent-source questions must count as failures.

Previously scored using original SAG2 BM25 (without Jev): 31/120 complete gold title @5, PGER V16 cheap initial retrieval 38/120, V16C 34/120. These are not direct comparisons with full SAG2 JEV.

## How to run the new V17B-to-JEV exact provider scorer comparison

From the checked-out repository's `v7-multihop` directory:

1. Fetch the same frozen corpus prepared by GitHub Actions:
   `gh run download 40741978291 --repo vjgits/Research-Papers --name pger-v17-hover-shared-120-claim-corpus --dir v17-hover-data/prepared`.
2. Clone the author source within `v7-multihop`, then pin:
   `git clone https://github.com/Zleap-AI/SAG-Benchmark.git sag-benchmark-v17`
   `git -C sag-benchmark-v17 checkout bb7f82751ba1576219f9d9ebd021128603d130c3`.
3. Install original SAG2 CPU indexing and API dependencies: `pip install aiohttp jieba==0.42.1 pyuca==1.2 python-dotenv regex tiktoken`; Python >=3.11, working C compiler and SQLite FTS5 needed. No local Qwen.
4. Run FREE preflight (NO API, no key):
   `python benchmark_v17_original_jev.py --max-cases 10 --budget-usd 1.00`
5. Only after explicitly approving provider spending, supply your key locally: `export OPENROUTER_API_KEY=...`. Prefer a local secret manager or terminal prompt; never paste in a chat or push to GitHub. In GitHub Actions, use a repository secret (not a committed .env).
6. Start 10 paid claims with approximate cumulative budget gate:
   `python benchmark_v17_original_jev.py --paid-run --max-cases 10 --budget-usd 1.00`
7. Once verified, full 120: `python benchmark_v17_original_jev.py --paid-run --max-cases 120 --budget-usd 2.00`, using a distinct output directory to avoid overwriting the pilot.
8. Cross-check response build `typesafe/jev-1.13-20260917`, actual model calls and provider charges, compare title AE@5/10/20 on exact IDs to archived V17 PGER output.

**Note:** The original `scripts/run_sag2_benchmark.py` only accepts MuSiQue, HotpotQA and 2Wiki as dataset arguments. Our independent HoVer wrapper reuses ORIGINAL `search_sag2`, `JevClient`, `CorpusIndex` without changing their algorithm; it is not a patch to the author pipeline. For a true original-paper reproduction on MuSiQue, run `uv run python scripts/run_sag2_benchmark.py --dataset musique --limit 10` from author `sag2/` with `.env` set, then expand to 1000, using pinned original source snapshots.

Nothing here makes source retrieval an established answer or proof. HoVer support/contradiction verdict correctness, evidence sentence selection, abstention and calibrated true/false judgments require additional scored evaluation. JEV's necessity probability is not a licensed independent factual proof.

**GitHub scripts:** `v7-multihop/benchmark_v17_original_jev.py` and `.github/workflows/pger_v17_jev_preflight.yml`, current branch `v17-hover-official-sag2-reproduction-2026-10-28`.
