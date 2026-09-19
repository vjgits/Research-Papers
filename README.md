# Research Papers

Open research artifacts by **Vijay Suresh** (Independent Researcher) on large language model reliability, evaluation, self-report, AI safety, and AI-driven economic transition.

**ORCID:** [0009-0004-1471-0561](https://orcid.org/0009-0004-1471-0561)

## Papers

### 1. Altitude Lock: More How, Still No Why

**Unprompted framing critique in LLM assistants, measured twice**  
Current version: **v2.5 · September 2026**

Every work request fixes choices nobody states — which outcome counts, over what horizon, for whom, by what measure, and whether the task is worth doing at all. None of them is false, so none trips a correction. This paper measures how often an assistant names one of those choices **and still does the work**, across two model generations three months apart on identical items. Unprompted surfacing rose from 5.2% to 23.3% (paired +18.1 pp, sign test p = 1.1e-6), though the frontier panel ranged from 12.5% to 43.3% and the leave-one-out rate is 16.7%. An arm that explicitly invited critique reached an asserting level in 52.7% of responses and completed the task in 0%, showing that framing engagement and task completion are separable and that an evaluation scoring critique alone can reverse intervention rankings.

- **Project folder:** [Altitude-Lock-More-How-Still-No-Why](./Altitude-Lock-More-How-Still-No-Why/)
- **Current PDF v2.5:** [Download manuscript](./Altitude-Lock-More-How-Still-No-Why/paper/v2.5/Altitude-Lock-More-How-Still-No-Why-v2.5.pdf)
- **Paper (all versions, concept DOI):** [doi:10.5281/zenodo.22847056](https://doi.org/10.5281/zenodo.22847056)
- **Data, code and figures (concept DOI):** [doi:10.5281/zenodo.22847075](https://doi.org/10.5281/zenodo.22847075)
- **arXiv:** pending endorsement

### 2. Emergent Deception in Large Language Models

**A Regime-Dependent Taxonomy and Pre-Registered Protocol for Model Self-Report**  
Current version: **v2.0 · September 2026**

This work defines **Emergent Deception (ED)** as a subset of LLM self-narration in which a self-referential proposition carries more apparent warrant than the available evidence supports without proportionate uncertainty. It develops a five-category taxonomy, two cross-cutting flags, motivating observational evidence, and a separately timestamped pre-registration for a 1,800-conversation confirmatory study.

- **Project folder:** [Emergent-Deception-in-Large-Language-Models](./Emergent-Deception-in-Large-Language-Models/)
- **Current paper v2.0:** [doi:10.5281/zenodo.22241085](https://doi.org/10.5281/zenodo.22241085)
- **Earlier Zenodo record / v1 lineage:** [doi:10.5281/zenodo.19802283](https://doi.org/10.5281/zenodo.19802283)
- **Pre-registration Protocol v1.3:** [doi:10.5281/zenodo.22245523](https://doi.org/10.5281/zenodo.22245523)
- **arXiv:** planned / pending submission

### 3. Boundary Contamination in LLM Workflows

**Paired experiments and audits of response and artifact acceptance**  
Current version: **v1.46 · September 2026** (previously titled *Observed Recoverable Behavioral Failures in LLM Workflows*)

Asking a model to check its work can improve the answer and still make the returned response unusable: the model corrects the figure, then wraps the corrected answer in commentary the task forbade. This paper defines **boundary contamination** as any non-whitespace text outside the required deliverable and scores it separately from whether the deliverable is correct. Across three experiments, checking-only instructions produced contamination in 14 of 30 held-out responses for one model and 0 of 30 for another under an identical prompt; one clause restating the output format suppressed it in 14 of 14 paired cases. The paper also audits its own measuring instrument, finding that 22 of 34 recorded failures were defects in the checker rather than in the responses.

- **Project folder:** [Boundary-Contamination-in-LLM-Workflows](./Boundary-Contamination-in-LLM-Workflows/)
- **Current PDF v1.46:** [Download manuscript](./Boundary-Contamination-in-LLM-Workflows/paper/v1.46/Boundary_Contamination_v1_46.pdf)
- **Paper:** [doi:10.5281/zenodo.22735762](https://doi.org/10.5281/zenodo.22735762)
- **Evidence archive:** [doi:10.5281/zenodo.22738017](https://doi.org/10.5281/zenodo.22738017)
- **All versions (concept DOI):** [doi:10.5281/zenodo.20271843](https://doi.org/10.5281/zenodo.20271843)
- **Earlier lineage (v1.23, v1.33) archived at:** [archive/Observed-Recoverable-Behavioral-Failures-in-LLM-Workflows](./archive/Observed-Recoverable-Behavioral-Failures-in-LLM-Workflows/)

### 4. Managing the AI Transition: Overshoot, Non-Replacement, and Adaptive Policy

**Foundational working paper · May 2026**

This paper reframes AI-driven labor disruption as a **dynamic transition-control problem** rather than only a static automation or substitution problem. It develops transition overshoot, the non-replacement mechanism, the capability-deployment gap, adaptive dampening, and a capital-market growth-pressure cascade; it also includes calibrated simulations and a public-data JOLTS exercise presented as suggestive rather than causally definitive.

- **Project folder:** [Managing-the-AI-Transition-Overshoot-Non-Replacement-and-Adaptive-Policy](./Managing-the-AI-Transition-Overshoot-Non-Replacement-and-Adaptive-Policy/)
- **Zenodo paper:** [doi:10.5281/zenodo.20078381](https://doi.org/10.5281/zenodo.20078381)

## Canonical Zenodo index

| Research object | DOI |
|---|---|
| Altitude Lock: More How, Still No Why — all versions (concept DOI) | [10.5281/zenodo.22847056](https://doi.org/10.5281/zenodo.22847056) |
| Altitude Lock — reproduction package, data and code (concept DOI) | [10.5281/zenodo.22847075](https://doi.org/10.5281/zenodo.22847075) |
| Emergent Deception in Large Language Models — current v2.0 | [10.5281/zenodo.22241085](https://doi.org/10.5281/zenodo.22241085) |
| Emergent Deception — earlier Zenodo record / v1 lineage | [10.5281/zenodo.19802283](https://doi.org/10.5281/zenodo.19802283) |
| Emergent Deception Pre-registration Protocol v1.3 | [10.5281/zenodo.22245523](https://doi.org/10.5281/zenodo.22245523) |
| Observed Recoverable Behavioral Failures in LLM Workflows | [10.5281/zenodo.20271844](https://doi.org/10.5281/zenodo.20271844) |
| Managing the AI Transition: Overshoot, Non-Replacement, and Adaptive Policy | [10.5281/zenodo.20078381](https://doi.org/10.5281/zenodo.20078381) |

## Repository organization

```text
Research-Papers/
├── README.md
├── CITATION.cff
├── Altitude-Lock-More-How-Still-No-Why/
├── Emergent-Deception-in-Large-Language-Models/
├── Boundary-Contamination-in-LLM-Workflows/
├── Managing-the-AI-Transition-Overshoot-Non-Replacement-and-Adaptive-Policy/
└── archive/
```

Each paper lives in its own top-level folder and carries its own README, citation metadata, licensing information, and research materials where available.

**Zenodo is the canonical archival/citation source for published versions; GitHub is the living companion repository for discoverability, reproducibility, code, version pointers, and future materials.**

If you use a construct, taxonomy, protocol, code artifact, or dataset from one of these projects, please cite the corresponding paper rather than this repository as a whole.

## Contact and reuse

Replication, critique, independent validation, and extensions are welcome. Open an issue or pull request in the relevant project where appropriate.
