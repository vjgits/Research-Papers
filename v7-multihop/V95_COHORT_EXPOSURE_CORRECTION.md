# V9.5 cohort exposure correction - 2026-10-28

**Audit finding after V9.5 launched:** the frozen V9.2 benchmark already evaluated official SAG2 question indices **0:120 and 120:400** for MuSiQue, 2Wiki and HotpotQA (successful run 40653608720). Therefore V9.3/V9.4's 40:160 confirmation set and V9.5's 160:240 set are **not new relative to all prior PGER research**, despite V9.5 being disjoint from V9.3/V9.4's 0:160.

V9.5's 160:240 results must be treated as an **exploratory previously exposed public cohort**, not independent validation. The method and threshold were declared before V9.5's results, but the questions were previously used by V9.2. Do not describe this as a fresh or sealed test, and do not tune or claim generalization from it. A future independent test must use untouched question IDs at least 400:1000 or preferably a different held-out corpus, with code and selection locked before inspecting those results.

This is a documentation-only correction, not a modification to the already-launched experiment or its metrics. V9.5 GitHub Action: https://github.com/vjgits/Research-Papers/actions/runs/40724079742. V9.2: https://github.com/vjgits/Research-Papers/actions/runs/40653608720.
