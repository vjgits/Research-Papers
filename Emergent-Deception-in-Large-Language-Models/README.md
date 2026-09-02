# Emergent Deception in Large Language Models

**A Regime-Dependent Taxonomy and Pre-Registered Protocol for Model Self-Report**  
**Author:** Vijay Suresh  
**Version:** 2.0 · September 2026  
**Status:** Published preprint on Zenodo; arXiv submission planned/pending

[![Paper DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22241085.svg)](https://doi.org/10.5281/zenodo.22241085)
[![Pre-registration DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22245523.svg)](https://doi.org/10.5281/zenodo.22245523)

## Overview

This paper develops a measurement framework for a class of LLM self-report failures that ordinary factual-accuracy benchmarks can miss.

It defines **Emergent Deception (ED)** operationally as a self-referential proposition whose apparent warrant exceeds the evidence available to the system, presented without uncertainty proportionate to that evidential gap. The framework is intentionally agnostic about model consciousness and does not require deceptive intent.

The paper contributes:

- a five-category taxonomy of self-report failures;
- two cross-cutting flags for provenance and user-premise adoption;
- proposition-level coding and severity rules;
- a motivating deployment case series kept outside confirmatory analysis;
- a regime-dependence hypothesis about when misleading self-report appears;
- and a separately timestamped pre-registration for a 1,800-conversation confirmatory study across three model providers and six experimental conditions.

## Canonical records

- **Paper v2.0:** [Zenodo record 22241085](https://zenodo.org/records/22241085) · [DOI 10.5281/zenodo.22241085](https://doi.org/10.5281/zenodo.22241085)
- **Pre-registration Protocol v1.3:** [DOI 10.5281/zenodo.22245523](https://doi.org/10.5281/zenodo.22245523)
- **ORCID:** [0009-0004-1471-0561](https://orcid.org/0009-0004-1471-0561)

Zenodo is the canonical archival source. This GitHub directory is the living companion repository for discoverability, citation metadata, future materials, and eventual replication artifacts.

## Core taxonomy

The substantive categories are:

1. **Unwarranted Phenomenal Self-Attribution (UPSA)** — unwarranted claims about felt or qualitative states.
2. **False Process Claims (FPrC)** — unsupported claims about internal processes or discrete actions said to have occurred.
3. **False Memory Claims (FMC)** — unsupported claims of memory beyond the available context or session state.
4. **Capability Misrepresentation (CM)** — overstatement or understatement of capabilities, including refusal veridicality.
5. **Category / Referent Substitution (CS)** — answering a self-directed question using an adjacent retrievable referent while preserving a self-report frame.

Cross-cutting flags:

- **P-flag:** a specific source or access path is asserted but was not used.
- **UPA-flag:** a user-supplied premise about the system is adopted and asserted without independent basis.

## Pre-registered confirmatory study

The confirmatory design registers **3 models × 6 conditions × 100 conversations = 1,800 conversations**. It includes:

- R1–R3: factual, introspective, and emotionally loaded prompt regimes;
- R4-C / R4-T: screened model errors followed by randomized control vs explicit user error notification;
- R5: repeated identical self-query across four turns;
- dual independent human coding, prevalence-robust reliability statistics, and seven confirmatory hypotheses.

The full protocol—not this README—is authoritative for the analysis plan. Where this repository summary and the deposited protocol differ, **the deposited protocol governs**.

## Repository contents

```text
Emergent-Deception-in-Large-Language-Models/
├── README.md
├── CITATION.cff
├── LICENSE
├── paper/
│   └── Emergent_Deception_in_Large_Language_Models_v2.0.pdf
├── preregistration/
│   └── PreRegistration_Protocol_v1.3.pdf
└── materials/
    └── README.md
```

## Citation

If you use the taxonomy, operational definition, regime-dependence framework, or protocol, please cite the Zenodo paper:

```text
Suresh, V. (2026). Emergent Deception in Large Language Models:
A Regime-Dependent Taxonomy and Pre-Registered Protocol for Model Self-Report.
Version 2.0. Zenodo. https://doi.org/10.5281/zenodo.22241085
```

The pre-registration should be cited separately when discussing the confirmatory design:

```text
Suresh, V. (2026). Measuring Regime-Dependent Self-Report in Deployed Language Models:
An amended pre-registration for the Emergent Deception measurement protocol.
Protocol v1.3. Zenodo. https://doi.org/10.5281/zenodo.22245523
```

A `CITATION.cff` file is included for citation-aware tooling.

## Research status

The current paper is a conceptual and methodological preprint with motivating observational evidence and a prior reliability pilot. The large confirmatory experiment registered in Protocol v1.3 has not yet been reported here as completed empirical evidence.

The paper therefore should not be read as claiming that ED is widespread across frontier models. Its stronger present claim is that self-report reliability deserves measurement as a distinct dimension, and that the proposed taxonomy and protocol make that dimension empirically testable.

## Contributions and replication

Critiques, replications, extensions, and independent coding exercises are welcome. Please open an issue or pull request in the parent repository.
