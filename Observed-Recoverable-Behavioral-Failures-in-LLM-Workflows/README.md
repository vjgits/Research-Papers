# Observed Recoverable Behavioral Failures in LLM Workflows

A Multi-Session Cross-Platform Case Study, Retry-Probe Pilot, and Multi-Model Evaluation Protocol

**Author:** Vijay Suresh · [ORCID](https://orcid.org/0009-0004-1471-0561)  
**Current repository version:** 1.33 · September 2026  
**Status:** Exploratory research preprint. The new version has not yet been deposited on Zenodo.

## Current manuscript and supporting material

- [Read the final PDF](paper/v1.33/Observed%20Recoverable%20Behavioral%20Failures%20in%20LLM%20Workflows.pdf)
- [Editable Word document](paper/v1.33/Observed%20Recoverable%20Behavioral%20Failures%20in%20LLM%20Workflows.docx)
- [Readable manuscript text](paper/v1.33/RBF_v1_33_Manuscript.md)
- [Research archive](paper/v1.33/RBF_v1_33_Research_Archive.zip): study records, artifacts, de-identified reviews, reproducibility scripts and historical materials
- [Manuscript source and figures](paper/v1.33/source/)

The 35-page manuscript retains sixteen observation definitions, sixteen tables and four figures. It separates content correctness, format compliance and artifact acceptance.

## Evidence and interpretation

Study 1 contains 576 responses in a constructed shared-anchor retry design. Across 144 A-to-E pairs, verification repaired two initial failures and introduced 29 regressions, all involving output format. Overall acceptance changed from 142/144 to 115/144. Checking and constraint-restatement effects are not separately identified.

Study 2 contains 100 scheduled incident-derived slots and 110 attempts including interrupted attempts and separate retries. Saved artifacts show explanatory inconsistencies and rendering defects. Reconstructions retain selected incident features; they are not exact historical replays.

The original human audit, separate AI review, browser rerendering and independent follow-up are distinct checks. The follow-up contains 36 scored outputs and 39 unscored entries, with unresolved disagreements. They are not pooled into a larger experiment. Future factorial and recovery-bank studies remain unexecuted. These studies do not estimate general-use error rates or establish vendor rankings.

## Versions and citation

The existing [Zenodo v1.23 record](https://doi.org/10.5281/zenodo.20271844) remains the published archival version. Its DOI must not be presented as a version-specific DOI for v1.33. The [all-version DOI](https://doi.org/10.5281/zenodo.20271843) links the Zenodo version lineage. Update the v1.33 citation after its new Zenodo deposit.

Until then, cite this repository version by title, author, version and commit. CITATION.cff describes v1.33 without assigning it the older version's DOI.

Older manuscripts and pilot tools remain in their original locations. [Earlier repository documentation](paper/README_pre_v1_33.md) describes historical runs and is superseded by the current manuscript's interpretation. Existing pilot scripts are not the collection protocol for the two current studies.

## Reproduction and reuse

Extract the research archive and start with its README.md and SHA256.json. It includes scripts to reproduce saved accounting without new model calls; accounting checks do not independently validate semantics. The current manuscript builder uses Python and python-docx, with LibreOffice used for PDF rendering. Older LaTeX sources describe older versions.

Manuscript: CC BY 4.0. Existing code licensing remains as recorded in LICENSE and the respective materials. Submitted reviewer labels and historical subject outputs are preserved. Do not give the unmasked research archive to a blinded evaluator.
