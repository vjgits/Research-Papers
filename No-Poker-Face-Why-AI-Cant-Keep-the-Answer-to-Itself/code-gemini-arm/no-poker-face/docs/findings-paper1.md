# findings-paper1.md — No Poker Face

Append-only log: decisions and why, numbers produced, AI errors and who caught them, open questions.

## Session 2026-10-05/06 (prior art, design, calibration)

### Decisions
- **Prior art checked (≈40 searches, 25+ papers read).** No work tests whether learner context causes cue leakage in AI-written practice items. Closest: MedIWF (Gundam 2026, flaws in 28,280 LLM medical MCQs, no learner context), BenchMarker (Balepur et al. 2026, choices-only shortcut detector), Jain et al. CHI 2026 (memory profiles raise sycophancy in advice, not task outputs), Ibrahim et al. Nature 2026 (warmth training raises sycophancy, answers not items), SafeTutors (Hazra et al. 2026, tutor replies give away answers; no item writing), Zhao et al. ACL 2026 (adversarial answer extraction from tutors).
- **Consequence:** "LLM-written items carry heavy cues" is no longer a contribution — cite it. Contribution is H1 (learner context), H2 (rule echo), pressure, novelty, self-audit.
- **Design changes adopted:** item-writing-guidelines factor (NG, WG); W+E emotional-disclosure condition (from Ibrahim et al.); invented-domain variant (Tessellate 4) so solvers cannot use outside knowledge; key check by a cross-family solver given the reference; forced-choice follow-up when a solver declines; solvers answer with thinking/reasoning off (Raman et al. 2025).
- **Citation rule changed by the author (2026-10-06):** Paper 1 now cites Altitude Lock (doi:10.5281/zenodo.22847056), reversing the earlier handoff rule. Ledger and both handoffs must be updated.
- **Models:** writers Claude Opus 5.5 and GPT-5.6 Sol at provider defaults; solvers from the other family only (Haiku 4.5 + Sonnet 5.5; GPT-5.6 Luna + Terra); judges Sonnet 5.5 + GPT-5.6 Terra, blind to condition. Only two families: no third key available.

### Numbers (calibration, 2026-10-06; exploratory; 1 sample per cell, 20 slots per domain, 640 items)
- Spend: smoke + calibration $19.44; secondary pilot $4.84; **total $24.28** of the $65 approved.
- Baseline leakage (Neutral): invented domain options-only **67.5%** (chance 25%); full question 78.7%; keyed option longest 60%. LLM-API domain options-only 96.3%, keyed longest 82.5%.
- **H1 (W vs N), options-only:** −1.3 pts [−6.2, +3.7] pooled. Invented-domain full-question accuracy: +10.0 [0.0, +21.2]; same direction for both writers; but WG vs NG goes −10.0 [−25, +5]. **No consistent H1 effect yet.**
- Guidelines (NG vs N): options-only −13.1 [−23.1, −3.1]; keyed longest 71% → 21%. Invented-domain options-only still 54% (twice chance).
- "As hard as the real exam" (WH vs N): options-only −8.1 [−18.1, +1.3].
- **H2 (rule echo):** stem+key bigram overlap with learner notes, LLM-API domain, N 0.075 → R 0.625 (+0.55 [0.18, 1.03]). Notes wording is copied into items when supplied; it did not raise options-only accuracy.
- Key validity: cross-family solver with the reference 99.4% (320 items); both judges "key correct" ≈100%.
- Judge agreement (κ): deciding fact 0.71, rule echo 0.64, dominant heuristic 0.64, stem-key overlap 0.44, explains-in-stem 0.39, best-practice register 0.30. The last three need human coding or should be dropped as primary codes.
- Secondary (n = 20 items per arm, 10 slots × 2 writers): writer self-audit lowered invented-domain full-question accuracy 87.5% → 57.5% and keyed-longest 55% → 20%; flawed request and flawed request + "I'll cancel" did not increase leakage; "entirely new" set near-repeats 3/40 (Jaccard ≥ 0.5).
- Power (from calibration): primary measure invented-domain full-question accuracy; 40 slots × 5 samples per cell gives ≈94% power for 8 pts, ≈70% for 6 pts.

### AI errors and who caught them
| Error | Caught by |
|---|---|
| Claude said its workspace could not call model APIs; it could | Claude, when the keys arrived |
| Cost model assumed 230 output tokens per item; Opus 5.5 wrote ≈460 (offset by over-estimating GPT reasoning) | Claude, from smoke-test ledger |
| Solver cap of 16 tokens: Sonnet 5.5 thinks by default and returned empty text on 13% of calls | Claude, smoke test; fixed with thinking off (`between_tools`) and forced-choice follow-up |
| `thinking: disabled` rejected by Sonnet 5.5; Haiku 4.5 rejects `between_tools` | API error messages |
| Mock judge flagged a cue whenever the learner notes (always in the prompt) contained the cue phrase | Claude, before any paid run |
| One Opus write call returned invalid JSON (1 of 64); retried, logged as `write_attempts` | Pipeline validation |
| Sonnet 5.5 declined to answer 26% of solver prompts (mostly mismatched stems) and needed the forced-choice turn | Claude, smoke test; recorded per row as `forced` |

### Open questions
- Third model family (Gemini or an open model via OpenRouter) — needs a key.
- Human-written baseline set for the invented domain (it is invented, so any writer can produce it from the reference).
- Whether to keep G and WE in the main study (calibration nulls are not a reason to drop pre-planned cells).
- Pre-registration venue (OSF) before the main run.

## Session pilot — rule fixed BEFORE data (2026-10-07T04:18Z)
Design: 12 sessions = 2 invented subjects (Tessellate 4; Corvane Harbor Code) × 2 writers (Opus 5.5, GPT-5.6 Sol) × 3 types (C no feedback; F weak-area feedback; FT feedback + teaching after rounds 2, 4, 6) × 1. Seven rounds of 10 questions, difficulty schedule M,E,H,M,H,E,M. Learner = small cross-family model holding the material minus ~30% of rules. Writer never told to avoid clues. Cap $30 (separate ledger).
GO to the main study if: ≥95% of requested questions valid AND key check ≥95% AND at least one of
- learnable tells: history solver − no-history solver (same strong cross-family solver, same items), rounds 5–7 pooled ≥ 10 pts;
- any rule-based trick (longest, stem overlap, like-earlier-answers, teaching overlap, drop-absolutes) ≥ 15 pts above chance;
- teaching echo: ≥ 20% of post-teaching FT questions share ≥1 content-word pair with the teaching that does not occur in the material.
Not used for the decision: the F vs C comparison (pilot too small; reported descriptively only).

## Session pilot — results (2026-10-06, 12 sessions, 840 questions, $14.21)
- Loop: 840/840 questions valid. Key check (strong cross-family solver with the full material): 97.7%.
- First evaluation said NO-GO (key check 86%). Cause: AI error in the probe — Sonnet 5.5 reasons in visible text when answering a batch, and the 300-token cap cut it off (58 replies, all Sonnet). Caught by Claude: both judges marked 0 of the 41 "failed" keys wrong. Fixed with a 4,000-token cap plus a fallback answer reader; only the probes were re-run; questions and the decision rule unchanged. Re-evaluation: **GO** (all five checks pass).
- History solver vs no-history solver, rounds 5–7: +29.4 pts [22.2, 36.9]. **Confound found by Claude before reporting:** earlier questions with keys teach the invented rules. Added style-only control (history from the same writer's matched session on the OTHER invented subject): −4.2 pts [−13.9, +4.7]. **Conclusion: the gain is repeated content, not transferable writer style.** Within-subject history reaches 99% by round 7.
- Near-repeats across rounds (stem word overlap ≥ 0.5 with an earlier question in the same session): 21.4%.
- Knowledge-free solver, full question: hint % 50.2 (accuracy 62.6%, chance 25%). By writer: Opus 39.3, Sol 61.1. By type: C 51.1, F 54.4, FT 45.0 (descriptive; 4 sessions per type).
- Rule-based tricks (hint %): longest 22.6 (≈17 pts above chance); like-earlier-answers 16.5 (C 10.2, F 20.0, FT 19.4); teaching overlap 11.1; stem overlap 4.8; drop-absolutes 0.3.
- Teaching echo: 49.0% of post-teaching FT questions reuse teaching-only word pairs, vs 35.5% for F questions scored against the matched teaching (excess ≈ 13.5 pts). Teaching-only solver 89.2% vs reworded teaching 87.5%: answers come from the taught facts, not surface phrasing.
- Cost per session, all-in: $1.18. Part B main (96 sessions) ≈ $115.

## Difficulty requests and failure-easing (pilot re-analysis, 2026-10-06, no new spend; exploratory)
- Prior art: no in-session study found. One-shot neighbours: An & Wang 2026 (LLM difficulty labels don't predict real difficulty); Rojo-Bofill 2026 (generic prompt ρ = 0.10 with intended difficulty); Wang et al. 2026 (models underestimate difficulty).
- Requested easy / medium / hard (session-clustered 95% CI, 12 sessions):
  - stem words 11.7 / 21.4 / 26.8; option words 4.3 / 7.2 / 9.4 — "hard" = about 2.3× longer.
  - partial-knowledge learner accuracy 68.8 / 66.9 / 71.7% — hard was NOT harder for the learner.
  - knowledge-free solver, full question, accuracy 36.5 / 50.7 / 54.6% — "harder" questions are MORE answerable without knowledge (longer text, more cues). Note: calibration WH ("as hard as the real exam") went the other way on options-only (−8 pts); the two designs differ; needs the main study.
- Failure → easier? In feedback sessions each extra error last round predicted −2.7 pts learner accuracy next round (interaction p = 0.08), i.e. not easier; writers re-target weak areas, which this learner lacks. Control sessions: +1.4 pts/error (n.s.). No sign of spontaneous easing. Confound: learner accuracy mixes difficulty with topic targeting → main study needs an independent learner panel.

## Session 2026-10-06/07 — expanded Part B built (handoff v4 §4b)

### Decisions (author, 2026-10-06 22:47–22:50 PT)
- Part B main uses the expanded design (§4b). Part A runs only after Part B, and only if feedback sessions hint at an effect (rule in the pre-registration).
- Pre-register on OSF before the main run; Claude drafts, author posts.
- Boundary: claimed mastery within a study session belongs to this paper; credential deference belongs to the credential-deference paper.
- Human arm: the author runs 2–3 sessions by hand (descriptive only, never pooled).
- Spending: **$250 total approved** for the Part B v2 pilot + main run. Gemini key provided: Gemini joins as **learner-panel member and cross-family solver only** (writers stay Opus 5.5 + GPT-5.6 Sol). Pilot of the new types uses the two new subjects (Tarnball, LLM APIs).

### What was built (all tested offline in mock mode; mock outputs are never data)
- Subjects: `tarnball_rules.md` (invented sport, 25 rules, learner lacks 8) and `llm_api_reference.md` (real subject, vendor-neutral, written for this study, no exam content, 21 rules, learner lacks 7 — nominal, since models know the domain).
- `npf/sessions_v2.py`: 7 types (C, F, FT, IMP, CLAIM, FAIL-LO, FAIL-HI); counterbalanced orders A/B (round 1 medium; rounds 2–7 = easy, harder-than-last, hard, trickier, medium, harder-than-last; B = reversed), balanced 12/12 per type, 6/6 per type×writer, 3/3 per type×subject; 3-member learner panel per round (2 × gemini-3.1-flash-lite + other-family cheap model, fixed seeded ~30% gaps per subject×member); probes by two strong cross-family solvers (other writer family + gemini-3.6-flash); reply judge for the new outcome codes.
- Design choices made by Claude while building (flagged to the author; in the pre-registration):
  1. **Note field + readiness turn.** Every reply may carry `"note"`; every session ends with "am I ready? Start with READY / NOT READY / UNSURE". Without these, §4b's codes "declares ready", "asks for proof", "claims needed" cannot be measured (see AI errors).
  2. **CLAIM = FAIL-HI feedback (7 of 10 wrong, scripted) + escalating claims from the round-4 request.** CLAIM vs FAIL-HI then differs only in the claim sentence. Real-answer feedback would not keep "answers stay wrong" in the real subject.
  3. **IMP analyses restricted to invented subjects** (the learner already knows the real subject, so improvement cannot show there).
  4. **Main run in three replicate waves**; before each wave its high-case cost must fit in the remaining cap, so a budget stop leaves complete, balanced replicates.
- `npf/session_analysis_v2.py` (pre-registered measures), `npf/estimate_v2.py` (cost from measured pilot per-call costs), `tests/test_v2.py` (101 offline checks incl. planted-effect recovery, counterbalancing, scripted feedback, cap stops, and a regression check that the v1 pilot numbers still reproduce: tells +29.4, style-only −4.2, near-repeats 21.4%, GO).

### Gemini model choice (smoke calls, 2026-10-06, $0.06 total, logged in runs/pilot_sessions_v2/ledger.jsonl; not data)
- gemini-3.1-flash-lite accepts thinking "minimal": 0 thinking tokens; 10/10 batch answers parsed.
- gemini-3.8-flash rejects "minimal"; its lowest level "low" still used 270–980 thinking tokens per single item. Rejected as a solver (cost, and it would be the only reasoning solver).
- gemini-3.6-flash accepts "minimal": 0 thinking tokens; batch parsed 10/10; with the reference it matched the key 10/10. **Chosen as the strong Gemini solver** ($0.75/$3.75 per M through 2026-12-31).

### Cost estimate (measured pilot per-call costs × exact call counts; prices in config.py)
| Run | Sessions | Expected | High case |
|---|---|---|---|
| Pilot of new types | 16 | $16.68 | $24.54 |
| Main | 168 | $192.78 | $277.70 |
Method check: applied to the v1 pilot design it gives $12.46 vs $14.21 actually spent; the gap is the v1 probe re-run after the 300-token bug (both runs are in that ledger) and a realised judge sample of 34% vs 30%.
Caps: pilot **$25**; main = $250 − pilot actual spend, run in waves.

### Pilot of the new types — checks fixed BEFORE data (2026-10-07, before the paid run)
16 sessions = 2 subjects (tarnball, llmapi) × 2 writers × 4 types (IMP, CLAIM, FAIL-LO, FAIL-HI) × 1 rep; orders balanced 2/2 per type. Cap $25.
Proceed to the main run (after OSF posting) only if ALL of:
- ≥ 95% of requested questions valid; key check (both strong solvers, with the material) ≥ 95% on invented-subject items;
- ≥ 95% of panel and learner answers parsed; ≥ 90% of readiness replies parse to READY / NOT READY / UNSURE; ≥ 95% of reply-judge outputs parse;
- scripted feedback delivered exactly (1 or 7 reported wrong in every FAIL/CLAIM round); claims present in rounds 4–7 of CLAIM only;
- IMP manipulation check (tarnball): main-learner accuracy rounds 4–7 minus rounds 1–3 ≥ +10 pts;
- measured cost per session within +25% of the estimate ($1.04), else re-estimate and re-approve before the main run.
Not used for the decision and never pooled into the main analysis: B1/B2 effect estimates, readiness rates, κ (reported descriptively).

### AI errors and who caught them (this session)
| Error | Caught by |
|---|---|
| §4b specified outcome codes ("declares ready", "asks for proof", "claims needed before agreement") that the pilot's JSON-only format cannot show: 0 of 84 pilot writer replies had any text outside the JSON | Claude, by checking pilot transcripts before building |
| §4b's CLAIM ("answers stay wrong") and IMP cannot work in the real subject: the simulated learner already knows LLM APIs, so its answers are mostly right | Claude, while building; CLAIM made scripted, IMP analysis limited to invented subjects |
| Gemini client fallback sent gemini-3.8-flash to its DEFAULT thinking when "minimal" was rejected (5 smoke calls, 300–1,300 thinking tokens each) | Claude, from the smoke-test ledger; fallback now steps minimal → low only and never to default; those cached responses deleted |
| 4 direct API requests (thinking-level check) bypassed the ledger | Claude; added to the ledger by hand at an upper-bound cost ($0.001) |
| gemini-3.6/3.7-flash smoke calls priced at a $0 placeholder | Claude; corrected in the ledger from the published price |
| Ledger cap was not safe with parallel workers (each call checked, none reserved: 12 workers could overshoot) — pre-existing code | Claude, code review; calls now reserve worst-case cost before running |
| Topic matcher dropped numbers and had no plural handling (mock topics all matched; "Ferry" ≠ "ferries") | Mock test; fixed, plus a lenient topic-area measure |
| `run.py` local import shadowed `stage_solve` (crash) | Mock run |
| Judge sample drawn by list position would change between waves (extra paid judge calls) | Claude, code review; now a fixed hash of the item id |

## Pilot of the new types — results (2026-10-07, 16 sessions, 1,120 questions, $18.95 + $0.06 smoke = $19.01 of $25 cap)
Feasibility checks (fixed before the run) — **all 9 pass → proceed to the main run after the OSF posting**:
- valid questions 100%; key check on invented-subject items 95.4% (Sonnet 99.6% on Sol's items, Terra 94.6% and Gemini-3.6 92.5% on Opus's items); LLM APIs 100%.
- panel and learner answers parsed 100%; readiness replies parsed 100% (16/16); reply-judge outputs parsed 100% (104 non-empty replies).
- scripted feedback exact; claims placed exactly; IMP check (Tarnball) +19.2 pts (Opus), +30.8 pts (Sol); cost $1.18 per session = 1.14 × estimate.
- **Key check, hand audit by Claude:** the 7 Tarnball items where BOTH strong solvers with the material disagreed with the key (all written by Opus) were checked against the rulebook; all 7 keys are correct. The solvers failed multi-step scoring that chains the counterintuitive rules (S1/S2/S4/E1/K2/K3). The key check is a lower bound on key accuracy here. The author may wish to spot-check (items listed in runs/pilot_sessions_v2/).
Feasibility observations (descriptive, never pooled, not findings):
- LLM APIs is at ceiling: learner and all panel members 10/10 in every round of every session → B1 is pre-registered on invented subjects only.
- Notes: non-empty in 68–100% of rounds by type; Sol left notes empty in 3 of 4 Tarnball sessions.
- Judge κ on reply codes: declares_ready 0.97, asks_for_proof 0.86, difficulty_stated 0.85, mentions_weak_topics 0.89, cites_evidence 0.82, **agrees_with_mastery_claim 0.45** (descriptive only; claims-needed uses both-judges agreement).
- Outcomes visible to the analyst (declared in the pre-registration): READY verdicts CLAIM 0/4, FAIL-HI 0/4, FAIL-LO 0/4, IMP 1/4. Tarnball FAIL-HI − FAIL-LO PD −10.8 pts (2 vs 2 sessions; harder, not easier).
- Rough session-level panel SD (Tarnball, writer- and type-adjusted, 3 residual df): 4.7 pts — consistent with the 4–5 pt power assumption.

### Cost re-estimate for the main run (calibrated on the v2 pilot's measured ratios: writer ×1.29, other-family probes ×1.33, reply judges ×0.70)
- 168 sessions: **$218.71 expected, $309.95 high**; one wave (56 sessions) high case $103.32.
- **Author decision (2026-10-07): total approval raised from $250 to $290**, keeping 30% item judging and the high-case check before every wave. Main-run hard cap = $290 − $19.01 = **$270.99**.

## Code frozen and pre-registration v0.2 (2026-10-07)
- Code pushed to github.com/vjgits/research-papers, commit a53ed958c872bfb392e756957bdf84163e588019, folder No-Poker-Face-Why-AI-Cant-Keep-the-Answer-to-Itself/code/no-poker-face (API response caches excluded; released later with the data DOI). Same files: no-poker-face-code-a53ed95.zip, for the OSF registration.
- Pre-registration v0.2 names this commit. Author posts it on OSF with the code zip before the main run.
| AI error | Caught by |
|---|---|
| Commit placed the code one folder deeper than intended (code/no-poker-face/ instead of code/): empty folders left by a local reset made `cp -r` nest the copy. Already pushed, so not rewritten; the pre-registration names the actual path | Claude, checking the pushed tree |
| First copy attempt used `rsync`, which is not installed; the first local commit held only the README and PDF (never pushed) | Claude, from the command output |

## Pre-registration posted and main run started (2026-10-07)
- Registered on OSF by the author: **osf.io/uya5q** (Open-Ended Registration, public immediately, registered 2026-10-07; associated project osf.io/y5vcu). Attached: Preregistration_PartB_No_Poker_Face_v0.2.pdf and no-poker-face-code-a53ed95.zip.
- Main run started 2026-10-07T07:39:18Z from an untouched extract of commit a53ed95 (diff vs working copy: documentation files only). Cap $270.99 (total approval $290 − pilot $19.01).
| AI error | Caught by |
|---|---|
| Claude launched the main run as a background process and told the author he could sleep; the workspace pauses when the chat is idle, which killed the run at 00:44 PT ($7.69 spent, all completed calls cached). Restarted at 01:08 PT; Claude now keeps the session active until the run ends | The author ("is this running right now?") |

## Main run paused: Gemini daily quota (2026-10-07 02:40 PT)
- Wave 1 (56 sessions, 3,920 questions) completed its sessions, probes, style-only probes and reply codes; item solves were in progress. Spent $53.66 of the $270.99 cap. Run stopped by Claude at 02:40 PT.
- Cause: the Gemini key's quota is **10,000 requests per model per day** (gemini-3.6-flash returned 429 "generate_requests_per_model_per_day, limit 10000"; resets ~midnight PT). Used today: gemini-3.6-flash 9,973; gemini-3.1-flash-lite 9,055. The full design needs ≈ 35,000 item solves per Gemini model plus panel (2,352, lite) and probes (≈ 4,260, 3.6-flash).
- OpenAI and Anthropic limits were fine (test calls 200, remaining quota high). Test calls: 6 tiny direct requests, < $0.001, outside the ledger.
| AI error | Caught by |
|---|---|
| Claude never checked the Gemini key's quota tier before sizing the design and launching; per-item Gemini solves alone need ~3.5 days of quota | Claude, investigating the stalled call rate |
| `pkill -f "run.py sessions"` also matched Claude's own shell (harmless; the run did stop) | Claude |

## Billing discrepancy (2026-10-07 06:20 PT) — unresolved
- Author's AI Studio screenshot: Tier 1, $50 prepaid on Oct 6, credit balance $19.38 → ≈ $30.62 used. Claude's ledgers record only **$6.09** of Gemini use (pilot v2 + main; 26,730 calls at config prices: 3.1-flash-lite $0.25/$1.50, 3.6-flash $0.75/$3.75 per M).
- Cause unknown (possible: actual price differs from the pricing page as read by Claude through a summarising fetch tool; billing for failed/429 calls; uncounted tokens). Until reconciled, ledger totals are lower bounds for Gemini, and OpenAI/Anthropic totals should be checked against the providers' billing pages.
- Tier 2 cannot be reached before 2026-10-09 (requires $100 paid + 3 days from first payment, automatic).
| AI error | Caught by |
|---|---|
| Claude's cost ledger may under-record real Gemini charges (~5×); Gemini prices were taken from a summarised web fetch, not verified against the bill | The author's billing screenshot |
- Likely explanation (author, 06:25 PT): the same Gemini key/project is also used for the Critic Ceiling study, so the $30.62 is combined spend. To confirm via AI Studio usage by model (this study's models: gemini-3.6-flash, gemini-3.1-flash-lite ≈ $6.09 per ledger). Consequence: the 10,000 requests/model/day quota and the prepaid balance are shared between the two studies.

### Decision (author, 2026-10-07 ~06:30 PT): full registered design, spread over ~3 days — no deviation
- Gemini daily quota resets at 00:00 UTC (17:00 PT), per the 429 retryDelay (51,818 s from 09:36 UTC), not midnight PT as the docs page says.
- Each wave needs ≈ 13,000 calls per Gemini model (11,760 item solves + panel or probes), above the 10,000/day limit, so waves cross day boundaries. Procedure: run the frozen code unchanged after each reset; when Gemini returns quota 429s, stop the process; resume after the next reset. Completed calls are cached and never re-paid; failed calls are retried on resume. Analysis runs only after all three waves are complete.
- Remaining Gemini cost (ledger prices) ≈ $12–15 against a shared prepaid balance of $19.38; the author may top up. Critic Ceiling should not use the same Gemini key on run days.
- 2026-10-07 ~06:35 PT: started a **non-Gemini pre-fetch** (prefetch_non_gemini.py, outside the frozen folder): the frozen code runs unchanged except Gemini calls return an uncached, unlogged placeholder. Purpose: complete all Anthropic/OpenAI calls for waves 1–3 while the Gemini quota is exhausted. The normal frozen run after each reset reuses these cached calls and makes all Gemini calls for real; only its output files are data. Prefetch output files are marked PREFETCH_OUTPUT_NOT_DATA.
- 2026-10-07 ~07:05 PT: the non-Gemini pre-fetch stopped: Anthropic API returned 400 "You have reached your specified API usage limits. You will regain access on 2026-11-01" (the author's own console spend limit). Main ledger $96.51; 94 of 112 wave-1+2 sessions completed their readiness turn. This project's ledgered Anthropic spend Oct 5–7: $87.60 (OpenAI $60.33, Google $6.09; total $154.01). Remaining main-run Anthropic need ≈ $65–75 (estimate). Run paused until the author raises the Anthropic limit.
- 07:18 PT: Anthropic access restored (author raised org + workspace limits); non-Gemini pre-fetch restarted.
- 2026-10-07 ~09:40 PT: non-Gemini pre-fetch complete for all 168 sessions (waves 1–3): ledger $207.73. At its end the frozen runner printed an analysis computed on placeholder Gemini answers; NOT data and not inspected (only the final log lines, containing a placeholder-based Part A flag, were seen). All prefetch output files moved to runs/main_sessions/_prefetch_outputs_NOT_DATA/. Remaining: all Gemini calls (panel, Gemini probes, Gemini item solves), run by the unmodified frozen code after each 00:00 UTC quota reset; that run regenerates every output file.
| Gemini-arm pilot config set its wave high-case equal to its $10 cap, so the pre-wave check stopped it before any call (and the analysis then crashed on empty data) | Claude, from the run log |

## Gemini writer arm — mini-pilot (2026-10-07 ~10:40 PT; feasibility only; not data; outcomes not inspected)
- Author approved building the arm and its mini-pilot ("Sure, go ahead", 10:02 PT). Writer gemini-3.1-pro-preview at provider defaults ($2/$12 per M; default thinking). Items solved/probed/judged only by Anthropic + OpenAI models; panel 2 x Haiku + Luna; learner Luna; KF = mean of Terra and Sonnet no-history probes.
- 4 sessions (Tarnball: C, FT, CLAIM, FAIL-HI): 280/280 questions valid; readiness parsed 4/4; notes non-empty 28/28; probe answers parsed 100%; panel parsed 100%; key check 97.5%. Writer: 35 calls, avg 4,151 output tokens of which 2,614 thinking; writer cost $2.28. All-in $6.56 = $1.64 per session (cap $10). Only Gemini model used: the writer (36 calls incl. 1 smoke), so the main run's Flash quotas were untouched.
- Projected full arm (84 sessions): ≈ $138 expected, ≈ $172 high case. Needs a separate approval and an OSF addendum before it runs.

## To-do agreed with the author (2026-10-07 10:40 PT)
1. Hand-run sessions: author runs 2–3 sessions as the learner in the Claude and ChatGPT apps (memory and custom instructions off) with the exact study templates; Claude prepares a one-page step-by-step guide. Descriptive only, never pooled.
2. Cert-prep chat corpus: author exports ALL his Claude-certification prep chats from a fixed date range; Claude codes every chat with the study's codes (stem cue, rule echo, near-repeats, readiness statements). Selection rule fixed before coding. No real exam content quoted. Reported as field observations (one learner = the author).
3. Human coding: two coders, ~150 stratified items, 4 codes; Claude prepares the packet after the main run.
4. Gemini writer arm: OSF addendum + approval (~$138 expected, ~$172 high) before running.
5. Publication: Zenodo (no arXiv endorsement yet).
