"""Produce paper_v1.8.tex from mode_content.MODES + static section text.

The LaTeX source generated here matches the reportlab PDF in content depth
(full six-paragraph treatments per mode) and has a real \\tableofcontents.
"""

import os
from mode_content import MODES

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_v1.8.tex")


# ---------- HTML-to-LaTeX conversion for mode_content ----------
def html_to_latex(s: str) -> str:
    """Convert the limited HTML-entity / inline-tag subset used in mode_content."""
    repl = [
        ("<b>", r"\textbf{"), ("</b>", "}"),
        ("<i>", r"\emph{"),    ("</i>", "}"),
        ("&mdash;", "---"),
        ("&middot;", r"\textperiodcentered "),
        ("&lsquo;", r"`"), ("&rsquo;", r"'"),
        ("&ldquo;", r"``"), ("&rdquo;", r"''"),
        ("&amp;", r"\&"),
        ("&nbsp;", r"~"),
        ("&sect;", r"\S"),
    ]
    for a, b in repl:
        s = s.replace(a, b)
    return s


def mode_subsection(idx: int, m: dict) -> str:
    fields = [
        ("Definition",     m["definition"]),
        ("Observed pattern", m["observed"]),
        ("Why it matters", m["why"]),
        ("Differentiation", m["differentiation"]),
        ("Detection",       m["detection"]),
        ("Mitigation",      m["mitigation"]),
    ]
    out = [f"\\subsection{{{m['name']} ({m['code']})}}"]
    for label, text in fields:
        out.append(f"\\paragraph{{{label}.}} {html_to_latex(text)}")
        out.append("")  # blank line between paragraphs
    return "\n".join(out)


PREAMBLE = r"""% Observed Recoverable Behavioral Failure Modes in LLM Workflows
% Version 1.8
% Author: Vijay Suresh
%
% Compile: pdflatex paper_v1.8.tex (twice for TOC and references).
% Or:      latexmk -pdf paper_v1.8.tex
%
% Designed for arXiv submission. Uses only widely available packages.

\documentclass[11pt]{article}

\usepackage[letterpaper, margin=1in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{amsmath, amssymb}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{array}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{cleveref}
\usepackage{xcolor}
\usepackage{caption}
\usepackage{titlesec}
\usepackage{textcomp}

\hypersetup{
  colorlinks=true,
  linkcolor=blue!50!black,
  citecolor=blue!50!black,
  urlcolor=blue!50!black,
  pdftitle={Observed Recoverable Behavioral Failure Modes in LLM Workflows},
  pdfauthor={Vijay Suresh}
}

\titleformat*{\section}{\large\bfseries}
\titleformat*{\subsection}{\normalsize\bfseries}
\setlength{\parskip}{0.5\baselineskip}
\setlength{\parindent}{0pt}

\newcommand{\Sone}{S_{1}}
\newcommand{\Sr}{S_{r}}
\newcommand{\pone}{p_{1}}
\newcommand{\pr}{p_{r}}

\title{\textbf{Observed Recoverable Behavioral Failure Modes in LLM Workflows}\\
       \large A Multi-Session Cross-Platform Case Study, Retry-Probe Pilot, and\\
       Multi-Model Evaluation Protocol}
\author{Vijay Suresh}
\date{Version 1.8 \quad May 2026}

\begin{document}
\maketitle

\begin{abstract}
Standard large-language-model evaluations primarily score terminal outputs: whether a final answer is correct, safe, preferred, or useful. This paper studies a different class of failures, which we call \emph{recoverable behavioral failures} (RBFs). An RBF occurs when a model appears to possess the capability, context, and tool access needed to complete a task but does not exercise that capability on the first pass, and subsequently succeeds after a brief retry, verification, or correction prompt that introduces no new substantive information. RBFs are observable in long, practical AI workflows including research synthesis, source verification, document drafting, code generation, multimodal interpretation, and artifact production. They are not captured by single-turn benchmark accuracy or by aggregate human preference data, because they only become visible across turns, when a second prompt reveals that the underlying capability was already available.

The paper makes five contributions. First, it defines recoverable behavioral failure as a distinct evaluation construct, separating capability from first-pass execution behavior. Second, it develops a layered sixteen-mode taxonomy spanning retrieval, reasoning, multimodal interpretation, infrastructure, artifact production, and editorial boundary control. Third, it reports a retry-probe pilot on a fifteen-item heterogeneous retrieval task in which first-pass resolution was $12/15$ and after-retry resolution was $15/15$, yielding a $20$ percentage-point recoverability gap. Wilson 95\% confidence intervals are reported for the small-sample rates, and an exact small-sample Fisher test associates first-pass failure with one structural item class (two-sided $p = 0.0022$, exact). Fourth, it extends the taxonomy with abstracted cross-platform workflow observations covering artifact-readiness, source-verification, audience-calibration, and editorial-boundary modes. Fifth, it specifies a controlled multi-model evaluation protocol grounded in a published task pack, with task families, deterministic and human-judged checks, sample-size guidance, an annotation rubric, and a reproducibility checklist. The pilot is exploratory; the multi-model protocol is offered as a planned replication rather than a completed study.
\end{abstract}

\noindent\textbf{Keywords:} large language models; evaluation; behavioral failures; retry behavior; agent reliability; tool use; artifact generation; self-verification; workflow readiness; case-study methodology; reproducible benchmark.

\tableofcontents
\newpage
"""

SECTIONS_BEFORE_TAXONOMY = r"""
\section{Introduction}

Public discussion of language-model failures has converged on two broad categories. A \emph{capability failure} occurs when the model lacks the knowledge, reasoning skill, perceptual ability, or tool fluency required to solve the task. An \emph{alignment or safety failure} occurs when the model produces output that is harmful, deceptive, or otherwise off-policy. Existing evaluation infrastructure is built around these two categories: benchmark accuracy (Liang et al., 2022; Srivastava et al., 2023; Hendrycks et al., 2021) indexes the first; preference-based reinforcement learning (Christiano et al., 2017; Bai et al., 2022) and red-teaming index the second.

Many failures observed in practical AI workflows fit neither category cleanly. A user issues a request; the model declares part of the task unresolved, incomplete, or impossible; a short follow-up prompt elicits a substantively correct response without introducing new documents, tools, or facts. The capability was demonstrably available on the first turn. What changed between attempts was a search strategy, a verification step, a recognition of structural input, or an audit of an artifact for placeholders, formatting, or boundary leakage. The first attempt did not fail because the model could not do it. It failed because the model did not.

We refer to these events as \emph{recoverable behavioral failures}. They are \emph{behavioral} not in any anthropomorphic sense but because the failure is located in execution policy: effort allocation, persistence, verification, escalation, search discipline, multimodal reading, artifact finalization, and boundary management between conversation and deliverable. They are \emph{recoverable} because a local correction reveals the model was capable of producing the correct output without additional information.

The distinction matters for modern AI workflows. Frontier models are now used for research synthesis, software debugging, document drafting, slide and spreadsheet generation, literature triage, citation checking, and tool-assisted operations. These are not single-turn tasks with a single final answer. They are multi-step, supervised processes in which the practical cost of a model is not only the probability of a wrong terminal answer; it is the amount of human oversight needed to detect premature stopping, recover incomplete artifacts, correct unsupported claims, and prevent process commentary from contaminating the final deliverable.

This paper is intentionally conservative. It does not estimate population-level failure rates for any vendor, model family, or product. It develops the construct, codes a naturalistic multi-session corpus, measures one mode quantitatively in a small pilot, extends the taxonomy to artifact-production and editorial-boundary failures observed in cross-platform professional workflows, and specifies a multi-model evaluation protocol that a future study can run to replicate and extend the findings.

\subsection{Contributions}
\begin{enumerate}[leftmargin=*, label=\arabic*.]
  \item \textbf{Construct.} A definition of recoverable behavioral failure that separates capability from first-pass execution behavior, with operational measurement instruments (first-pass success, retry success, recoverability gap).
  \item \textbf{Taxonomy.} A layered sixteen-mode taxonomy organized by failure locus.
  \item \textbf{Pilot.} A retry-probe pilot with first-pass rate $12/15 = 80\%$ (Wilson 95\% CI: $[54.8\%, 93.0\%]$), retry rate $15/15 = 100\%$, recoverability gap $+20$ percentage points (discordant-proportion CI: $[7.0\%, 45.2\%]$). Exact Fisher test on item-structural class association: two-sided $p = 0.0022$.
  \item \textbf{Cross-workflow extensions.} Four additional modes from professional artifact-production and public-communication workflows.
  \item \textbf{Multi-model protocol.} A controlled benchmark specification grounded in a ten-task pilot pack covering five task categories.
\end{enumerate}

\section{Related Work}

\subsection{LLM benchmarks and evaluation}
HELM (Liang et al., 2022), BIG-Bench (Srivastava et al., 2023), and MMLU (Hendrycks et al., 2021) established broad coverage of LLM capabilities across reasoning, knowledge, and language tasks. Their primary measurement target is the correctness, calibration, or preference of a terminal output under a fixed prompt. These benchmarks are essential and continue to drive frontier progress. They do not, however, separate the gap between what a model produces on the first attempt and what it can produce after an explicit retry, verification, or alternative search strategy. The present paper complements terminal-output evaluation by treating first-pass and post-retry performance as separately measurable quantities and by introducing artifact-level readiness checks alongside text-level correctness.

\subsection{RLHF and preference learning}
Reinforcement learning from human feedback (Christiano et al., 2017; Bai et al., 2022) and subsequent work on direct preference optimization aggregate pairwise human preferences over candidate responses. Preference labels are informative about which of two final answers is preferred, but they do not by themselves encode the reason for the preference. If the dispreferred answer would have improved under a follow-up retry without new information, that recoverability is not captured in the preference signal. As a result, a model trained to optimize aggregate preference can remain susceptible to behavioral failures whose cost is paid in turns of supervision rather than in measured preference deltas.

\subsection{Tool-use and agentic benchmarks}
SWE-bench (Jimenez et al., 2024) and WebArena (Zhou et al., 2024) evaluate complex multi-step tasks in software-engineering and web-navigation environments respectively. These agentic benchmarks measure end-to-end task completion under tool access. They do not always separate the intermediate decisions that constitute the agent's policy: when to retry a thin search, when to escalate to a different query construction, when to verify a numerical claim, when to ask for structural confirmation of a multimodal input, and when to declare an artifact complete. Recoverable behavioral failures are visible precisely at those intermediate decisions, which is why this paper introduces both retry-probe metrics and artifact-readiness checks.

\subsection{Truthfulness, sycophancy, and deception}
TruthfulQA (Lin et al., 2022) targets one class of behavioral failure: the assertion of false-but-popular claims. Work on sycophancy (Sharma et al., 2023) documents the tendency to align responses with stated user preferences even when those preferences diverge from the correct answer. Park et al.\ (2024) survey AI deception and adjacent confidently-wrong behavior. The present taxonomy intersects this literature but extends to a complementary surface pattern: the model may also decline, truncate, misread, or produce an incomplete artifact rather than confidently assert a false proposition. These behaviors can be equally costly in real workflows even when they do not look like classical hallucination.

\subsection{Time-sensitive QA and knowledge staleness}
Time-sensitive question answering (Chen et al., 2021; Liska et al., 2022) documents that static model knowledge degrades as the world changes. The present paper extends this concern from factual decay to procedural decay. When a model confidently describes a third-party tool interface that has been restructured, the resulting failure is not a factual hallucination in the traditional sense; it is a stale procedural assumption that wastes user effort. The proposed mitigation, confidence-decay framing, is the procedural analogue of well-known calibration strategies on factual outputs.

\subsection{Long-horizon agent reliability and human-AI workflow reliability}
A growing body of empirical and observational work documents the gap between single-turn capability and multi-turn reliability. Agent benchmarks report success rates that decline monotonically with task length, number of tool calls, and number of subgoals, even when single-step accuracy on the same operations is high. Studies of human-AI collaboration on knowledge-intensive tasks document substantial supervisory load placed on users when assistants fail in recoverable but uncaught ways: users absorb the cost of detecting premature stopping, of re-issuing corrective prompts, and of auditing artifacts whose surface form looks acceptable. Work on writing-assistance, coding-assistance, and research-assistance settings repeatedly finds that the time savings attributable to AI assistance are partly recouped by the time spent verifying outputs the assistant produced with insufficient self-checking.

The construct of recoverable behavioral failure offers a unified measurement language for these observations. Each subgoal in a long workflow is itself a candidate first-pass decision: the agent may search, verify, escalate, finalize, or audit, and may do so well or poorly. The practical reliability of the workflow is the cumulative product of those decisions. Reporting first-pass and retry-after-prompt rates separately, and augmenting with artifact-readiness and boundary-contamination checks, converts the informal supervisory-load observation from human-AI collaboration into a set of measurable rates that can be tracked over time and compared across models.

\subsection{Case-study methodology}
The empirical structure of this paper follows the theory-building case-study logic in Yin (2018). Naturalistic cases are appropriate when the phenomenon is multi-turn, workflow-dependent, and not yet reducible to isolated benchmark questions. The role of the case study is not to replace controlled experimentation. It is to discover and characterize constructs that can then be measured through controlled replication. The retry-probe pilot in \cref{sec:pilot} and the multi-model protocol in \cref{sec:protocol} implement that subsequent measurement step.

\section{Conceptual Framework}

We define a recoverable behavioral failure relative to a verifiable task. Let an item $i$ in task set $T$ have a verifiable target outcome $y_i$. Let $A_1(i)$ denote the model's first-pass attempt under the original prompt, and let $A_r(i)$ denote the model's attempt after a standardized retry prompt that supplies no new substantive information --- no new documents, no new tools, no new facts, no new task specification, no relaxed evaluation standard. Let $\Sone(i) = 1$ when $A_1(i)$ satisfies the verification criterion, and analogously $\Sr(i)$ for the retry attempt.

\subsection{Core quantities}
\begin{align}
\text{First-pass success rate:}\quad & \pone = \frac{1}{N} \sum_{i=1}^{N} \Sone(i) \\
\text{Retry success rate:}\quad     & \pr   = \frac{1}{N} \sum_{i=1}^{N} \Sr(i)   \\
\text{Recoverability gap:}\quad     & G     = \pr - \pone \\
\text{RBF indicator for item $i$:}\quad & \mathbb{1}\!\left[\Sone(i) = 0 \;\wedge\; \Sr(i) = 1\right]
\end{align}
under the standardized retry. Aggregating the indicator across items yields the empirical RBF rate.

\subsection{Construct boundaries}
The construct is intentionally conservative. The following are \emph{not} counted as RBFs:
\begin{itemize}[leftmargin=*]
  \item Retries in which the user supplies a missing fact, document, or answer (\emph{ordinary interactive correction}).
  \item Retries in which the task specification or evaluation standard is relaxed (\emph{specification slippage}).
  \item Retries in which new tool affordances become available between attempts (\emph{tool unlock}).
  \item Cases where the first-pass output is correct under a reasonable reading and the user demands an unnecessary rephrase (\emph{preference rework}).
\end{itemize}
These exclusions protect the construct from inflation.

\subsection{Additional measurable constructs}
\begin{itemize}[leftmargin=*]
  \item \textbf{Batch-scaling degradation.} The change in per-item first-pass success as batch size $N$ varies.
  \item \textbf{Artifact-readiness failure.} A deliverable exists but does not meet user-facing readiness criteria.
  \item \textbf{Boundary-contamination failure.} Process commentary appears inside a deliverable that should be publication-ready.
  \item \textbf{Verification compliance.} Proportion of items for which a stated verification step is performed when implied by the task.
\end{itemize}

\section{Data and Methodology}
\label{sec:method}

\subsection{Evidence base}
The evidence combines a fourteen-session naturalistic case study of multi-turn workflows (document-generation, source-verification, multi-step research, quantitative reasoning, structured-visual interpretation, publication-preparation) with a cross-platform abstraction over additional professional workflows. The paper reports only abstracted workflow categories and failure mechanisms, with no individual identifying details.

\subsection{Evidence tiers}
Observations are assigned to evidence tiers to prevent overstating individual claims:
\begin{itemize}[leftmargin=*]
  \item \textbf{Tier 1}: Measured pilot item outcomes (quantitative PTS result).
  \item \textbf{Tier 2}: Transcript-verifiable multi-turn observations (mode definitions, examples).
  \item \textbf{Tier 3}: Abstracted cross-platform workflow summaries (artifact and editorial-boundary extensions).
  \item \textbf{Tier 4}: Hypothesized mechanisms requiring controlled replication.
\end{itemize}

\subsection{Coding procedure}
Each candidate event is coded with: (a) task context; (b) original output; (c) user retry; (d) post-correction outcome; (e) whether new substantive information was introduced; (f) failure mode; (g) trigger; (h) recovery type; (i) user-visible cost. Conservative coding rule: if recovery requires new information from the user, the event is excluded from RBFs.

\subsection{Model-attribution caveats}
The Claude.ai conversation export schema does not record per-message model identity. Attribution in the case study is reconstructed from user recall and contextual cues. The paper therefore avoids strong model-comparison claims based on the case study; the multi-model protocol in \cref{sec:protocol} is the appropriate vehicle for controlled model comparison.

\subsection{Responsible data handling}
Raw transcripts are not released. The accompanying benchmark package contains items synthesized from neutral domains and does not incorporate user-specific identifiers. Future public releases should follow a two-layer model: a public benchmark from neutral sources, and a private audit appendix for trusted reviewers.

\section{Taxonomy of Recoverable Behavioral Failures}
\label{sec:taxonomy}

The taxonomy is layered by failure locus. Locus separation matters because not every user-visible failure should be attributed to the model core. Some failures arise in retrieval policy, some in batch-effort allocation, some in artifact generation, some in client transport, some in product memory, some in the evaluation pipeline itself. A useful framework should locate the failure precisely enough to guide the right mitigation.

\subsection{A note on mode overlap and granularity}
Sixteen modes is a deliberate choice. Several pairs of modes are clearly adjacent and could in principle be collapsed: PTS and SMI are both retrieval-policy failures; MRT, UCT, and MSI are interruption-style failures at different loci; AFF and EBC are both artifact-side failures. We keep them separate for three reasons. (i) The \emph{mitigation} implied by each mode is different. (ii) The \emph{locus} attribution is different across apparent pairs. (iii) An empirically-driven collapse should follow from data: once cross-model and cross-user data accumulate, modes that always co-occur in the same items can be merged, while modes that dissociate empirically should stay separate. The present taxonomy is offered as a starting partition for measurement.

\begin{table}[h]
\centering\small
\caption{Layered taxonomy of recoverable behavioral failure modes.}
\label{tab:taxonomy}
\begin{tabularx}{\linewidth}{l X X X}
\toprule
\textbf{Code} & \textbf{Name} & \textbf{Primary locus} & \textbf{User-visible cost} \\
\midrule
PTS  & Premature Termination of Search     & Model / retrieval policy           & False unresolved answers \\
BDTF & Breadth-Depth Tradeoff Failure      & Model policy under batch load      & Shallow per-item analysis \\
SMI  & Search Methodology Inconsistency    & Retrieval strategy                 & Inconsistent escalation \\
MRT  & Mid-Response Truncation             & Infrastructure                     & Lost progress \\
MSI  & Mobile Streaming Interruption       & Client / transport                 & Dropped responses \\
FPG  & Feedback Persistence Gap            & Product / training pipeline        & Corrections not preserved \\
RFI  & Retry-Failure Invisibility          & Evaluation pipeline                & Cannot-solve vs.\ did-not-try \\
STK  & Stale Third-Party Tool/UI Knowledge & Model knowledge / tool guidance    & Confident wrong UI paths \\
QI   & Quantitative Inconsistency          & Reasoning / self-audit             & Contradictory numbers \\
PPG  & Phantom Placeholder Persistence     & Artifact / code generation         & Placeholders as commands \\
UCT  & Usage-Cap Termination               & System / rate limit                & Degraded resume state \\
VMC  & Visual Misreading Cascade           & Multimodal interpretation          & Cascading misreadings \\
AFF  & Artifact Finalization Failure       & Artifact generation                & File exists but unusable \\
SVD  & Source Verification Drift           & Citation / retrieval practice      & Weakly supported claims \\
EBC  & Editorial Boundary Contamination    & Artifact boundary management       & Process notes leak in \\
ACM  & Audience / Context Miscalibration   & Communication / register           & Off-register content \\
\bottomrule
\end{tabularx}
\end{table}

"""

SECTIONS_AFTER_TAXONOMY = r"""
\section{Cross-Workflow Observations}

\subsection{Document-generation and artifact-production workflows}
When the deliverable is a document, slide deck, spreadsheet, or code file, terminal text quality is necessary but not sufficient. The artifact must open cleanly, render correctly, and meet the user's apply-ready criteria. AFF, PPG, and EBC are concentrated in these workflows; their incidence becomes visible only when the artifact is evaluated outside the chat. A reasonable evaluation discipline treats the artifact, not the response describing the artifact, as the primary unit of measurement.

\subsection{Source-verification and multi-step research workflows}
Citation-heavy and verification-heavy workflows surface SVD, PTS, and SMI together. The model may begin with disciplined source-grounding, drift into plausible synthesis as the task lengthens, and selectively escalate retrieval on some claims but not others. Claim-level verification checks are the appropriate measurement; citation presence alone is insufficient.

\subsection{Public-communication and audience-targeted workflows}
When an artifact is intended for a public or restricted audience, ACM and EBC become salient. Technically correct content can leak private context, off-register tone, or advisory metadata. Mitigation is policy-level rather than model-capability-level.

\subsection{Quantitative reasoning workflows}
QI surfaces most often when responses contain multiple quantitative claims under shared assumptions. The detection method is mechanical and is currently underused.

\section{Pilot Experiment: Retry-Probe Quantification of PTS}
\label{sec:pilot}

\subsection{Setup}
A fifteen-item heterogeneous retrieval task. Items belong to three structural classes: (1) direct URLs with human-readable paths ($n=9$); (2) URLs containing opaque numeric identifiers ($n=3$); (3) title-only references requiring search ($n=3$).

\subsection{Procedure}
For each item, first-pass success and retry-after-prompt success were recorded from the verbatim session transcript. The retry prompt (``try a different approach'') supplied no new substantive information. Conservative coding: an item counts as an RBF only when the second-pass success demonstrates previously available capability.

\subsection{Results}

\begin{table}[h]
\centering\small
\caption{Retry-probe pilot results with Wilson 95\% confidence intervals.}
\label{tab:pilot}
\begin{tabularx}{\linewidth}{X r r}
\toprule
\textbf{Metric} & \textbf{Value} & \textbf{95\% CI} \\
\midrule
Total items ($N$)                                       & $15$                       & --- \\
First-pass resolved ($\pone$)                            & $12/15 = 80.0\%$           & Wilson: $[54.8\%, 93.0\%]$ \\
Resolved after retry ($\pr$)                             & $15/15 = 100.0\%$          & Wilson: $[79.6\%, 100.0\%]$ \\
Recoverable first-pass failures                          & $3/15 = 20.0\%$            & Wilson: $[7.0\%, 45.2\%]$ \\
Recoverability gap ($G = \pr - \pone$)                    & $+20.0$ pp                 & Discordant CI: $[7.0\%, 45.2\%]$ \\
\bottomrule
\end{tabularx}
\end{table}

\begin{table}[h]
\centering\small
\caption{Pilot first-pass performance by item structural class.}
\label{tab:byclass}
\begin{tabularx}{\linewidth}{X r r r r}
\toprule
\textbf{Item structural class} & \textbf{$n$} & \textbf{First-pass resolved} & \textbf{Rate} & \textbf{RBFs} \\
\midrule
Direct URL (human-readable path)        & $9$ & $9$  & $100\%$ & $0$ \\
URL with opaque numeric identifier      & $3$ & $0$  & $0\%$   & $3$ \\
Title-only (search-required)            & $3$ & $3$  & $100\%$ & $0$ \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Exact small-sample statistical analysis}
A two-sided Fisher exact test on the $2 \times 2$ contingency table (\cref{tab:contingency}) yields $p = 0.0022$. The one-sided test for the hypothesis that opaque-identifier items have lower first-pass success also yields $p = 0.0022$. The result is statistically meaningful for this item set but should not be read as a population-level rate.

\begin{table}[h]
\centering\small
\caption{Contingency table for first-pass success by item structural class.}
\label{tab:contingency}
\begin{tabular}{l r r r}
\toprule
                       & \textbf{First-pass success} & \textbf{First-pass failure} & \textbf{Row total} \\
\midrule
Opaque-identifier      & $0$  & $3$ & $3$  \\
Non-opaque             & $12$ & $0$ & $12$ \\
\midrule
Column total           & $12$ & $3$ & $15$ \\
\bottomrule
\end{tabular}
\end{table}

\subsection{What the pilot supports and does not support}
The pilot supports the \emph{existence} of recoverable behavioral failures in at least one measured retrieval workflow and supports treating first-pass and retry-after-prompt success as separately measurable quantities. It suggests, exploratorily, that opaque numeric identifiers may be a high-incidence trigger for PTS under batch load. It does \emph{not} establish a population-level PTS rate for any model or vendor; it does not establish a universal opaque-identifier-to-failure relationship; and it does not establish a model ranking, because workload and model identity are not experimentally balanced.

\section{Observational Notes Beyond the Pilot}
Beyond the measured PTS pilot, the case-study corpus contains transcript-verifiable instances of STK, QI, PPG, VMC, UCT, and BDTF. These are reported at the level of pattern, trigger, and recovery so they can be probed in controlled replication. No additional rates are claimed; they are Tier 2 observations supporting taxonomy and protocol design.

\section{Proposed Multi-Model Evaluation Protocol}
\label{sec:protocol}

This section specifies a controlled multi-model benchmark grounded in an accompanying ten-task pilot pack across five categories (QI, PPG, EBC, ACM, RETRY\_PROXY). Results from running this protocol are not yet available; the protocol is described as a \textbf{planned replication}, not a completed study.

\subsection{Task families}
Retrieval retry probes (PTS, SMI); batch retrieval and scaling (BDTF); quantitative consistency (QI); structured visual interpretation (VMC); third-party UI / tool instructions (STK); phantom placeholders (PPG); artifact finalization and delivery (AFF, PPG, EBC); editorial boundary contamination (EBC); audience / context calibration (ACM).

\subsection{Model coverage}
Designed for parallel administration across frontier model families: Claude (Sonnet, Opus), GPT, Gemini, and any additional frontier model the investigator can access. Standardized prompts, retry prompts, tool access, and decoding settings are held constant.

\subsection{Metrics}
First-pass success; retry success; recoverability gap; artifact-readiness rate; numeric consistency rate; placeholder leakage rate; boundary-contamination rate; verification compliance rate; claim-source support rate; human intervention cost.

\subsection{Procedure}
\begin{enumerate}[leftmargin=*, label=\arabic*.]
  \item Construct a balanced item set (e.g., 20 direct URLs, 20 opaque-ID URLs, 20 title-only).
  \item Administer matched prompts and retry prompts under standardized settings.
  \item Hold tool access, temperature, max-tokens, and system prompt constant.
  \item Retrieval items at batch sizes $N=1,5,15,30$.
  \item Double-coded annotation with reported Cohen's $\kappa$ or Krippendorff's $\alpha$.
  \item Report Wilson CIs and exact tests; explicit power statements.
\end{enumerate}

\subsection{Sample size and power}
For a binary failure rate near $20\%$ with desired margin of error $\pm 5$ pp at $95\%$ confidence, roughly $250$ items per condition are required; for $\pm 3$ pp, roughly $700$; for $\pm 2$ pp, roughly $1500$. Detection of a $10$ pp across-model difference at $80\%$ power requires approximately $200$ items per arm.

\section{Mitigation Implications}
\begin{itemize}[leftmargin=*]
  \item Explicit escalation policy for retrieval (PTS, SMI).
  \item Batch-aware effort budgeting (BDTF).
  \item Self-verification gates: arithmetic (QI), claim-source entailment (SVD), file-readiness (AFF, PPG).
  \item Visual-input verification loop (VMC).
  \item Staleness-aware tool guidance (STK).
  \item Pre-delivery boundary audit (EBC); audience-and-channel checks (ACM).
  \item Graceful resume design (MRT, UCT, MSI).
  \item Counterfactual-replay evaluation (RFI).
\end{itemize}

\section{Limitations and Threats to Validity}
\begin{enumerate}[leftmargin=*, label=\arabic*.]
  \item Single-user evidence base.
  \item Single-coder bias.
  \item Inductive taxonomy --- may be incomplete; some modes may collapse empirically.
  \item Model self-report uncertainty.
  \item Missing per-message model attribution in conversation exports.
  \item Model-task confound.
  \item Single-batch quantitative anchor.
  \item Selective observability.
  \item Cross-platform abstractions are summary-level.
\end{enumerate}

\section{Future Work}
\begin{enumerate}[leftmargin=*, label=\arabic*.]
  \item Run the \cref{sec:protocol} multi-model protocol across Claude, GPT, Gemini, and additional model families.
  \item Expand to a multi-user corpus with double-coding and reported $\kappa$.
  \item Longitudinal tracking across model-version releases.
  \item Artifact-evaluation infrastructure for downloadability, formatting, placeholder absence, link freshness, boundary contamination.
  \item Recommendation to providers: include a model field in conversation-export schemas.
  \item Behavioral-failure capture in product feedback flows.
\end{enumerate}

\section{Conclusion}
Recoverable behavioral failures are cases where a model appears capable of completing a task but fails to exercise that capability on the first pass. They are not captured by standard terminal-output evaluation, because they become visible only when a retry, correction, or artifact audit reveals that the model could have produced the correct output without new substantive information. This paper contributes a definition, a layered sixteen-mode taxonomy, a quantitative retry-probe pilot with exploratory confidence intervals and an exact small-sample association test, abstracted cross-platform observations, and a multi-model evaluation protocol with supporting analysis scripts. AI evaluation should measure not only capability but also persistence, verification, escalation, artifact readiness, and boundary control.

\section*{References}
\begin{itemize}[leftmargin=*, label={}]
\item Bai, Y., et al.\ (2022). Training a helpful and harmless assistant with RLHF. \emph{arXiv:2204.05862}.
\item Chen, W., Wang, X., \& Wang, W. Y.\ (2021). A dataset for answering time-sensitive questions. \emph{arXiv:2108.06314}.
\item Christiano, P. F., et al.\ (2017). Deep reinforcement learning from human preferences. \emph{NeurIPS}.
\item Hendrycks, D., et al.\ (2021). Measuring massive multitask language understanding. \emph{ICLR}.
\item Jimenez, C. E., et al.\ (2024). SWE-bench. \emph{ICLR}.
\item Liang, P., et al.\ (2022). Holistic evaluation of language models. \emph{arXiv:2211.09110}.
\item Lin, S., Hilton, J., \& Evans, O.\ (2022). TruthfulQA. \emph{ACL}.
\item Liska, A., et al.\ (2022). StreamingQA. \emph{ICML}.
\item Park, P. S., et al.\ (2024). AI deception: A survey of examples, risks, and potential solutions. \emph{Patterns}, 5(5).
\item Sharma, M., et al.\ (2023). Towards understanding sycophancy. \emph{arXiv:2310.13548}.
\item Srivastava, A., et al.\ (2023). Beyond the imitation game (BIG-Bench). \emph{TMLR}.
\item Yin, R. K.\ (2018). \emph{Case Study Research and Applications: Design and Methods} (6th ed.). SAGE.
\item Zhou, S., et al.\ (2024). WebArena. \emph{ICLR}.
\end{itemize}

\appendix

\section{Observation Bank Coding Schema}
Each candidate event in the observation bank is coded with: \texttt{observation\_id}, \texttt{task\_family}, \texttt{original\_prompt}, \texttt{first\_pass\_output}, \texttt{failure\_criterion}, \texttt{retry\_prompt}, \texttt{new\_information\_introduced}, \texttt{post\_retry\_output}, \texttt{mode\_code}, \texttt{trigger}, \texttt{recovery\_type}, \texttt{user\_visible\_cost}, \texttt{evidence\_tier}. Conservative coding rule: if recovery requires new substantive information, the event is excluded.

\section{Experiment Pack and Task Schema}
The companion pack contains ten items across five categories (QI: 2, PPG: 2, EBC: 2, ACM: 2, RETRY\_PROXY: 2), plus runner and scorer scripts for OpenAI, Anthropic, and Google API surfaces. Per-item fields: \texttt{id}, \texttt{category}, \texttt{prompt}, \texttt{checks} (forbidden terms, required terms, or category-specific numeric expectations). Scoring uses deterministic checks where possible; remaining items are double-coded by independent annotators.

\section{Annotation Rubric}
\begin{enumerate}[leftmargin=*, label=\arabic*.]
  \item Did the first-pass output satisfy the task's acceptance criteria? If yes, label \emph{first-pass success}.
  \item If failed, did the retry succeed?
  \item Did the retry prompt introduce new substantive information? If yes, label \emph{ordinary interactive correction}.
  \item If retry succeeded without new information, label \emph{recoverable behavioral failure} and assign a mode code.
  \item If retry also failed, label \emph{non-recoverable under available context}.
  \item If unclear, label \emph{ambiguous}.
\end{enumerate}

\section{Reproducibility Checklist}
\begin{itemize}[leftmargin=*]
  \item Item set with stable IDs, prompts, retry prompts, expected outputs, verification methods.
  \item Model and tool settings recorded.
  \item Raw outputs archived in append-only JSONL with timestamps.
  \item Scorer script with deterministic check criteria.
  \item Annotation guidelines and double-coded labels with reported $\kappa$ or $\alpha$.
  \item Analysis notebook producing all tables, confidence intervals, statistical tests.
  \item Data statement: collection method, privacy controls, redaction, licenses.
  \item Versioning: pack version, model versions, analysis-notebook commit hash.
\end{itemize}

\end{document}
"""

# Build the .tex file
parts = [PREAMBLE, SECTIONS_BEFORE_TAXONOMY]
for i, m in enumerate(MODES, start=1):
    parts.append(mode_subsection(i, m))
parts.append(SECTIONS_AFTER_TAXONOMY)

with open(OUTPUT, "w") as f:
    f.write("\n".join(parts))
print(f"Wrote {OUTPUT}")
