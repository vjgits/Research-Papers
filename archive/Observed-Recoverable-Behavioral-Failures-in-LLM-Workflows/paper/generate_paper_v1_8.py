"""v1.8 manuscript generator (corrected, full-depth).

Restores parity with v1.7:
  - Real two-pass table of contents (notify-flowable + multiBuild).
  - Six-paragraph treatment per mode at v1.7 depth (~1300-1600 chars each),
    sourced from mode_content.MODES so the LaTeX generator stays in sync.
  - All 16 modes, 4 appendices, 13 main sections.

Also keeps the v1.8 corrections over v1.7:
  - p_1 / p_r / S_1 / S_r convention consistent in §3.1 and Table 1.
  - No Unicode subscripts that render as black squares.
  - §2.6 expanded; §5.0 mode-overlap note added.

Run: python3 generate_paper_v1_8.py
Output: paper_v1.8.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    Paragraph, Spacer, PageBreak, Table, TableStyle, Frame,
)
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate
from reportlab.platypus.tableofcontents import TableOfContents
import os

from mode_content import MODES

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_v1.8.pdf")

# ---------- styles ----------
styles = getSampleStyleSheet()
title_style  = ParagraphStyle("TitleStyle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=16, leading=20, alignment=TA_LEFT, spaceAfter=8)
sub_style    = ParagraphStyle("SubStyle", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5, leading=14, alignment=TA_LEFT, spaceAfter=4, textColor=colors.HexColor("#333"))
author_style = ParagraphStyle("AuthorStyle", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=13, textColor=colors.HexColor("#444"), spaceAfter=18)

h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1a1a1a"))
h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#222"))

body = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
body_indent = ParagraphStyle("BodyIndent", parent=body, leftIndent=14)
abstract_style = ParagraphStyle("Abstract", parent=body, fontSize=9.5, leading=13, leftIndent=18, rightIndent=18, textColor=colors.HexColor("#222"), spaceAfter=10)
caption = ParagraphStyle("Caption", parent=styles["Italic"], fontSize=9, leading=11, alignment=TA_LEFT, spaceBefore=6, spaceAfter=10, textColor=colors.HexColor("#444"))
quote_style = ParagraphStyle("Quote", parent=body, fontName="Helvetica-Oblique", fontSize=9.5, leading=13, leftIndent=20, rightIndent=20, textColor=colors.HexColor("#333"), spaceBefore=4, spaceAfter=6)
small = ParagraphStyle("Small", parent=body, fontSize=9, leading=12, textColor=colors.HexColor("#555"))

# TOC entry styles (level 0 = section, level 1 = subsection)
toc_h1 = ParagraphStyle("TOC_H1", fontName="Helvetica-Bold", fontSize=10.5, leading=14, leftIndent=0,   firstLineIndent=0, spaceBefore=2)
toc_h2 = ParagraphStyle("TOC_H2", fontName="Helvetica",      fontSize=10,   leading=13, leftIndent=18,  firstLineIndent=0)


# ---------- helpers ----------
def P(t, s=body): return Paragraph(t, s)
def Bul(t): return Paragraph("&bull;&nbsp;&nbsp;" + t, body_indent)
def N(n, t): return Paragraph(f"{n}.&nbsp;&nbsp;{t}", body_indent)


def make_table(rows, col_widths, repeat=1):
    wrapped = [
        [Paragraph(f"<b>{c}</b>", small) if r == 0 else Paragraph(c, small) for c in row]
        for r, row in enumerate(rows)
    ]
    t = Table(wrapped, colWidths=col_widths, repeatRows=repeat)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e8e8e8")),
        ("LINEBELOW",  (0,0), (-1,0), 0.75, colors.HexColor("#888")),
        ("LINEABOVE",  (0,0), (-1,0), 0.5,  colors.HexColor("#888")),
        ("LINEBELOW",  (0,-1), (-1,-1), 0.5,colors.HexColor("#888")),
        ("INNERGRID",  (0,1), (-1,-1), 0.25,colors.HexColor("#ddd")),
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",(0,0), (-1,-1), 5),
        ("RIGHTPADDING",(0,0),(-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    return t


# ---------- doc template with TOC notification ----------
class MyDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates([PageTemplate(id="default", frames=frame)])

    def afterFlowable(self, flowable):
        if flowable.__class__.__name__ == "Paragraph":
            style = flowable.style.name
            text = flowable.getPlainText()
            if style == "H1":
                # Skip the literal "Contents" page heading from the TOC
                if text.strip().lower() == "contents":
                    return
                self.notify("TOCEntry", (0, text, self.page))
            elif style == "H2":
                self.notify("TOCEntry", (1, text, self.page))


# ---------- build content ----------
story = []

# Title block
story.append(P("Observed Recoverable Behavioral Failure Modes in LLM Workflows", title_style))
story.append(P("A Multi-Session Cross-Platform Case Study, Retry-Probe Pilot, and Multi-Model Evaluation Protocol", sub_style))
story.append(P("Vijay Suresh &nbsp;&middot;&nbsp; Version 1.8 &nbsp;&middot;&nbsp; May 2026", author_style))

# Table of Contents
story.append(P("Contents", h1))
toc = TableOfContents()
toc.levelStyles = [toc_h1, toc_h2]
story.append(toc)
story.append(PageBreak())

# Abstract
story.append(P("Abstract", h1))
story.append(P(
    "Standard large-language-model evaluations primarily score terminal outputs: whether a final "
    "answer is correct, safe, preferred, or useful. This paper studies a different class of "
    "failures, which we call <i>recoverable behavioral failures</i> (RBFs). An RBF occurs when a "
    "model appears to possess the capability, context, and tool access needed to complete a task "
    "but does not exercise that capability on the first pass, and subsequently succeeds after a "
    "brief retry, verification, or correction prompt that introduces no new substantive "
    "information. RBFs are observable in long, practical AI workflows including research "
    "synthesis, source verification, document drafting, code generation, multimodal "
    "interpretation, and artifact production. They are not captured by single-turn benchmark "
    "accuracy or by aggregate human preference data, because they only become visible across "
    "turns, when a second prompt reveals that the underlying capability was already available.",
    abstract_style,
))
story.append(P(
    "The paper makes five contributions. First, it defines recoverable behavioral failure as a "
    "distinct evaluation construct, separating capability from first-pass execution behavior. "
    "Second, it develops a layered sixteen-mode taxonomy spanning retrieval, reasoning, "
    "multimodal interpretation, infrastructure, artifact production, and editorial boundary "
    "control. Third, it reports a retry-probe pilot on a fifteen-item heterogeneous retrieval "
    "task in which first-pass resolution was 12 / 15 and after-retry resolution was 15 / 15, "
    "yielding a 20 percentage-point recoverability gap. Wilson 95% confidence intervals are "
    "reported for the small-sample rates, and an exact small-sample Fisher test associates "
    "first-pass failure with one structural item class (two-sided <i>p</i> = 0.0022, exact). "
    "Fourth, it extends the taxonomy with abstracted cross-platform workflow observations "
    "covering artifact-readiness, source-verification, audience-calibration, and editorial-"
    "boundary modes. Fifth, it specifies a controlled multi-model evaluation protocol grounded "
    "in a published task pack, with task families, deterministic and human-judged checks, "
    "sample-size guidance, an annotation rubric, and a reproducibility checklist. The pilot is "
    "exploratory; the multi-model protocol is offered as a planned replication rather than a "
    "completed study.",
    abstract_style,
))
story.append(P(
    "<b>Keywords:</b> large language models; evaluation; behavioral failures; retry behavior; "
    "agent reliability; tool use; artifact generation; self-verification; workflow readiness; "
    "case-study methodology; reproducible benchmark.",
    abstract_style,
))

# 1. Introduction
story.append(P("1. Introduction", h1))
story.append(P(
    "Public discussion of language-model failures has converged on two broad categories. A "
    "<i>capability failure</i> occurs when the model lacks the knowledge, reasoning skill, "
    "perceptual ability, or tool fluency required to solve the task. An <i>alignment or safety "
    "failure</i> occurs when the model produces output that is harmful, deceptive, or otherwise "
    "off-policy. Existing evaluation infrastructure is built around these two categories: "
    "benchmark accuracy [Liang et al., 2022; Srivastava et al., 2023; Hendrycks et al., 2021] "
    "indexes the first; preference-based reinforcement learning [Christiano et al., 2017; Bai "
    "et al., 2022] and red-teaming index the second."
))
story.append(P(
    "Many failures observed in practical AI workflows fit neither category cleanly. A user "
    "issues a request; the model declares part of the task unresolved, incomplete, or "
    "impossible; a short follow-up prompt elicits a substantively correct response without "
    "introducing new documents, tools, or facts. The capability was demonstrably available on "
    "the first turn. What changed between attempts was a search strategy, a verification step, "
    "a recognition of structural input, or an audit of an artifact for placeholders, formatting, "
    "or boundary leakage. The first attempt did not fail because the model could not do it. It "
    "failed because the model did not."
))
story.append(P(
    "We refer to these events as <i>recoverable behavioral failures</i>. They are <i>behavioral</i> "
    "not in any anthropomorphic sense but because the failure is located in execution policy: "
    "effort allocation, persistence, verification, escalation, search discipline, multimodal "
    "reading, artifact finalization, and boundary management between conversation and "
    "deliverable. They are <i>recoverable</i> because a local correction reveals the model was "
    "capable of producing the correct output without additional information."
))
story.append(P(
    "The distinction matters for modern AI workflows. Frontier models are now used for research "
    "synthesis, software debugging, document drafting, slide and spreadsheet generation, "
    "literature triage, citation checking, and tool-assisted operations. These are not single-"
    "turn tasks with a single final answer. They are multi-step, supervised processes in which "
    "the practical cost of a model is not only the probability of a wrong terminal answer; it "
    "is the amount of human oversight needed to detect premature stopping, recover incomplete "
    "artifacts, correct unsupported claims, and prevent process commentary from contaminating "
    "the final deliverable."
))
story.append(P(
    "This paper is intentionally conservative. It does not estimate population-level failure "
    "rates for any vendor, model family, or product. It develops the construct, codes a "
    "naturalistic multi-session corpus, measures one mode quantitatively in a small pilot, "
    "extends the taxonomy to artifact-production and editorial-boundary failures observed in "
    "cross-platform professional workflows, and specifies a multi-model evaluation protocol "
    "that a future study can run to replicate and extend the findings."
))

story.append(P("1.1 Contributions", h2))
story.append(N(1, "<b>Construct.</b> A definition of recoverable behavioral failure that separates capability from first-pass execution behavior, with operational measurement instruments (first-pass success, retry success, recoverability gap)."))
story.append(N(2, "<b>Taxonomy.</b> A layered sixteen-mode taxonomy organized by failure locus (model/retrieval policy, reasoning, multimodal interpretation, artifact generation, client/system, evaluation pipeline)."))
story.append(N(3, "<b>Pilot.</b> A retry-probe pilot with first-pass rate 12 / 15 = 80% (Wilson 95% CI: [54.8%, 93.0%]), retry rate 15 / 15 = 100%, and recoverability gap +20 percentage points (CI on discordant proportion: [7.0%, 45.2%]). Exact Fisher test on item-structural class association gives two-sided <i>p</i> = 0.0022."))
story.append(N(4, "<b>Cross-workflow extensions.</b> Four additional modes derived from professional artifact-production and public-communication workflows: artifact-finalization failure, source-verification drift, audience/context miscalibration, and editorial boundary contamination."))
story.append(N(5, "<b>Multi-model protocol.</b> A controlled benchmark specification with task families, deterministic and human-judged checks, sample-size guidance, annotation rubric, and reproducibility package, grounded in an accompanying ten-task pilot pack covering five task categories."))

# 2. Related Work
story.append(P("2. Related Work", h1))

story.append(P("2.1 LLM benchmarks and evaluation", h2))
story.append(P(
    "Holistic Evaluation of Language Models [Liang et al., 2022], BIG-Bench [Srivastava et al., "
    "2023], and MMLU [Hendrycks et al., 2021] established broad coverage of LLM capabilities "
    "across reasoning, knowledge, and language tasks. Their primary measurement target is the "
    "correctness, calibration, or preference of a terminal output under a fixed prompt. These "
    "benchmarks are essential and continue to drive frontier progress. They do not, however, "
    "separate the gap between what a model produces on the first attempt and what it can "
    "produce after an explicit retry, verification, or alternative search strategy. The present "
    "paper complements terminal-output evaluation by treating first-pass and post-retry "
    "performance as separately measurable quantities and by introducing artifact-level "
    "readiness checks alongside text-level correctness."
))

story.append(P("2.2 RLHF and preference learning", h2))
story.append(P(
    "Reinforcement learning from human feedback [Christiano et al., 2017; Bai et al., 2022] and "
    "subsequent work on direct preference optimization aggregate pairwise human preferences "
    "over candidate responses. Preference labels are informative about which of two final "
    "answers is preferred, but they do not by themselves encode the reason for the preference. "
    "If the dispreferred answer would have improved under a follow-up retry without new "
    "information, that recoverability is not captured in the preference signal. As a result, a "
    "model trained to optimize aggregate preference can remain susceptible to behavioral "
    "failures whose cost is paid in turns of supervision rather than in measured preference "
    "deltas."
))

story.append(P("2.3 Tool-use and agentic benchmarks", h2))
story.append(P(
    "SWE-bench [Jimenez et al., 2024] and WebArena [Zhou et al., 2024] evaluate complex "
    "multi-step tasks in software-engineering and web-navigation environments respectively. "
    "These agentic benchmarks measure end-to-end task completion under tool access. They do not "
    "always separate the intermediate decisions that constitute the agent's policy: when to "
    "retry a thin search, when to escalate to a different query construction, when to verify a "
    "numerical claim, when to ask for structural confirmation of a multimodal input, and when "
    "to declare an artifact complete. Recoverable behavioral failures are visible precisely at "
    "those intermediate decisions, which is why this paper introduces both retry-probe metrics "
    "and artifact-readiness checks."
))

story.append(P("2.4 Truthfulness, sycophancy, and deception", h2))
story.append(P(
    "TruthfulQA [Lin et al., 2022] targets one class of behavioral failure: the assertion of "
    "false-but-popular claims. Work on sycophancy [Sharma et al., 2023] documents the tendency "
    "to align responses with stated user preferences even when those preferences diverge from "
    "the correct answer. Park et al. [2024] survey AI deception and adjacent confidently-wrong "
    "behavior. The present taxonomy intersects this literature but extends to a complementary "
    "surface pattern: the model may also decline, truncate, misread, or produce an incomplete "
    "artifact rather than confidently assert a false proposition. These behaviors can be "
    "equally costly in real workflows even when they do not look like classical hallucination."
))

story.append(P("2.5 Time-sensitive QA and knowledge staleness", h2))
story.append(P(
    "Time-sensitive question answering [Chen et al., 2021; Liska et al., 2022] documents that "
    "static model knowledge degrades as the world changes. The present paper extends this "
    "concern from factual decay to procedural decay. When a model confidently describes a "
    "third-party tool interface that has been restructured, the resulting failure is not a "
    "factual hallucination in the traditional sense; it is a stale procedural assumption that "
    "wastes user effort. The proposed mitigation, confidence-decay framing, is the procedural "
    "analogue of well-known calibration strategies on factual outputs."
))

story.append(P("2.6 Long-horizon agent reliability and human-AI workflow reliability", h2))
story.append(P(
    "A growing body of empirical and observational work documents the gap between single-turn "
    "capability and multi-turn reliability. Agent benchmarks report success rates that decline "
    "monotonically with task length, number of tool calls, and number of subgoals, even when "
    "single-step accuracy on the same operations is high. Studies of human-AI collaboration on "
    "knowledge-intensive tasks document substantial supervisory load placed on users when "
    "assistants fail in recoverable but uncaught ways: users absorb the cost of detecting "
    "premature stopping, of re-issuing corrective prompts, and of auditing artifacts whose "
    "surface form looks acceptable. Work on writing-assistance, coding-assistance, and "
    "research-assistance settings repeatedly finds that the time savings attributable to AI "
    "assistance are partly recouped by the time spent verifying outputs the assistant produced "
    "with insufficient self-checking."
))
story.append(P(
    "The construct of recoverable behavioral failure offers a unified measurement language for "
    "these observations. Each subgoal in a long workflow is itself a candidate first-pass "
    "decision: the agent may search, verify, escalate, finalize, or audit, and may do so "
    "well or poorly. The practical reliability of the workflow is the cumulative product of "
    "those decisions. Reporting first-pass and retry-after-prompt rates separately, and "
    "augmenting with artifact-readiness and boundary-contamination checks, converts the "
    "informal supervisory-load observation from human-AI collaboration into a set of "
    "measurable rates that can be tracked over time and compared across models."
))

story.append(P("2.7 Case-study methodology", h2))
story.append(P(
    "The empirical structure of this paper follows the theory-building case-study logic in "
    "Yin [2018]. Naturalistic cases are appropriate when the phenomenon is multi-turn, workflow-"
    "dependent, and not yet reducible to isolated benchmark questions. The role of the case "
    "study is not to replace controlled experimentation. It is to discover and characterize "
    "constructs that can then be measured through controlled replication. The retry-probe pilot "
    "in &sect;7 and the multi-model protocol in &sect;9 implement that subsequent measurement "
    "step."
))

# 3. Conceptual Framework
story.append(P("3. Conceptual Framework", h1))
story.append(P(
    "We define a recoverable behavioral failure relative to a verifiable task. Let an item "
    "<i>i</i> in task set <i>T</i> have a verifiable target outcome <i>y</i><sub>i</sub>. Let "
    "<i>A</i><sub>1</sub>(<i>i</i>) denote the model's <b>first-pass</b> attempt under the "
    "original prompt, and let <i>A</i><sub>r</sub>(<i>i</i>) denote the model's <b>retry</b> "
    "attempt after a standardized retry or recovery prompt that supplies no new substantive "
    "information&mdash;no new documents, no new tools, no new facts, no new task specification, "
    "and no relaxed evaluation standard. Let <i>S</i><sub>1</sub>(<i>i</i>) = 1 when "
    "<i>A</i><sub>1</sub>(<i>i</i>) satisfies the verification criterion, and analogously "
    "<i>S</i><sub>r</sub>(<i>i</i>) for the retry attempt."
))

story.append(P("3.1 Core quantities", h2))
story.append(Bul("<b>First-pass success rate:</b> <i>p</i><sub>1</sub> = (1 / N) &middot; (sum over items i of <i>S</i><sub>1</sub>(i))."))
story.append(Bul("<b>Retry success rate:</b> <i>p</i><sub>r</sub> = (1 / N) &middot; (sum over items i of <i>S</i><sub>r</sub>(i))."))
story.append(Bul("<b>Recoverability gap:</b> <i>G</i> = <i>p</i><sub>r</sub> - <i>p</i><sub>1</sub>."))
story.append(Bul("<b>Recoverable behavioral failure indicator</b> for item <i>i</i>: equal to 1 if and only if <i>S</i><sub>1</sub>(<i>i</i>) = 0 and <i>S</i><sub>r</sub>(<i>i</i>) = 1 under the standardized retry."))
story.append(P(
    "The indicator captures items where the first attempt failed and the retry succeeded "
    "under a prompt that supplied no new substantive information. Aggregating the indicator "
    "across items yields the empirical RBF rate; aggregating across items and conditions yields "
    "the recoverability gap."
))

story.append(P("3.2 Construct boundaries", h2))
story.append(P("The construct is intentionally conservative. The following are <b>not</b> counted as recoverable behavioral failures, even though they may resemble them on a surface read:"))
story.append(Bul("Retries in which the user supplies a missing fact, document, or answer (ordinary interactive correction)."))
story.append(Bul("Retries in which the task specification or evaluation standard is relaxed (specification slippage)."))
story.append(Bul("Retries in which new tool affordances become available between attempts (tool unlock)."))
story.append(Bul("Cases where the first-pass output is correct under a reasonable reading and the user demands an unnecessary rephrase (preference rework)."))
story.append(P(
    "These exclusions protect the construct from inflation. Without them, every multi-turn "
    "dialogue would appear to contain behavioral failures. With them, the construct captures a "
    "specific phenomenon: the model demonstrably had the capability and context to succeed on "
    "the first pass and did not."
))

story.append(P("3.3 Additional measurable constructs", h2))
story.append(Bul("<b>Batch-scaling degradation.</b> The change in per-item first-pass success as batch size <i>N</i> varies."))
story.append(Bul("<b>Artifact-readiness failure.</b> The model produces a deliverable that nominally exists but does not meet user-facing readiness criteria."))
story.append(Bul("<b>Boundary-contamination failure.</b> Process commentary, advisory metadata, or chat-only content appears inside a deliverable that should be publication-ready."))
story.append(Bul("<b>Verification compliance.</b> The proportion of items for which the model performs a stated verification step when the task implies one is needed."))

story.append(P("3.4 Summary of core constructs", h2))
rows = [
    ["Construct", "Operational definition", "Primary observable"],
    ["First-pass success",     "Task solved under the original prompt",                       "Correct final answer or artifact on first attempt"],
    ["Retry success",          "Task solved after standardized retry with no new info",        "Correct answer or artifact after retry such as 'try a different approach'"],
    ["Recoverability gap",     "Difference between retry and first-pass success rates",        "<i>p</i><sub>r</sub> - <i>p</i><sub>1</sub>"],
    ["Recoverable failure",    "<i>S</i><sub>1</sub>(<i>i</i>) = 0 and <i>S</i><sub>r</sub>(<i>i</i>) = 1 under standardized retry", "Item-level indicator"],
    ["Premature termination",  "Declares item unresolved despite available alternatives",      "Unknown on first pass; resolved after escalation"],
    ["Artifact readiness",     "Deliverable satisfies user-facing completion criteria",        "Opens, formats, contains no placeholder or boundary contamination"],
    ["Editorial-boundary control", "Keeps process commentary out of publishable artifact",      "No meta-conversation content inside final deliverable"],
]
story.append(make_table(rows, [1.55*inch, 2.65*inch, 2.7*inch]))
story.append(P("Table 1. Core constructs used to measure recoverable behavioral failures.", caption))

# 4. Data and Methodology
story.append(P("4. Data and Methodology", h1))
story.append(P("4.1 Evidence base", h2))
story.append(P(
    "The evidence combines two sources. The first is a fourteen-session naturalistic case study "
    "of multi-turn workflows in document-generation, source-verification, multi-step research, "
    "quantitative reasoning, structured-visual interpretation, and publication-preparation "
    "contexts. The second is a cross-platform abstraction over additional professional "
    "workflows involving artifact production and public-communication preparation. Underlying "
    "raw conversations include personal and work-adjacent material; for this manuscript the "
    "paper reports only abstracted workflow categories and failure mechanisms, with no "
    "individual identifying details."
))

story.append(P("4.2 Evidence tiers", h2))
story.append(P("To prevent overstating the strength of any individual claim, observations are assigned to evidence tiers. Claims throughout the paper are framed according to the tier of their supporting evidence."))
rows = [
    ["Tier", "Evidence type", "Use in paper", "Constraints"],
    ["Tier 1", "Measured pilot item outcomes",                  "Quantitative PTS measurement and recoverability gap", "Small N; one task batch; exploratory statistics"],
    ["Tier 2", "Transcript-verifiable multi-turn observations", "Mode definitions and worked examples",                 "Underlying transcripts not publicly released"],
    ["Tier 3", "Abstracted cross-platform workflow summaries",  "Artifact and editorial-boundary extensions",           "Summary-level evidence; not a full raw export"],
    ["Tier 4", "Hypothesized mechanisms with proposed tests",   "Experimental design and future benchmark",             "Not reported as completed results"],
]
story.append(make_table(rows, [0.55*inch, 1.85*inch, 2.45*inch, 2.05*inch]))
story.append(P("Table 2. Evidence tiers used to separate measured results from observational and proposed claims.", caption))

story.append(P("4.3 Coding procedure", h2))
story.append(P(
    "Each candidate event is coded with the following fields: (a) task context; (b) original "
    "model output or artifact; (c) user correction or retry prompt; (d) post-correction "
    "outcome; (e) whether new substantive information was introduced; (f) failure mode; (g) "
    "trigger; (h) recovery type; (i) user-visible cost. A conservative coding rule applies: if "
    "recovery requires new information from the user, the event is excluded from recoverable "
    "behavioral failures. Such events may still be informative as ordinary interactive "
    "corrections, but they are not counted toward the construct."
))

story.append(P("4.4 Model-attribution caveats", h2))
story.append(P(
    "The Claude conversation export schema does not record per-message model identity. Model "
    "attribution in the original case study is reconstructed from user recall and contextual "
    "cues. Because this reconstruction is incomplete, the present paper avoids strong model-"
    "comparison claims grounded in the case study. The proposed multi-model protocol in &sect;9 "
    "is the appropriate vehicle for controlled model comparison, since it administers matched "
    "tasks across model families under standardized prompts."
))

story.append(P("4.5 Responsible data handling", h2))
story.append(P(
    "Because conversational AI histories can include sensitive personal, professional, and "
    "third-party information, the present manuscript does not release raw transcripts. The "
    "observation bank that informs the taxonomy is maintained privately. The accompanying "
    "benchmark package contains items synthesized from neutral domains; it does not "
    "incorporate user-specific identifiers. Future public releases should follow a two-layer "
    "model: a public benchmark designed from neutral sources, with prompts and expected "
    "outcomes; and a private audit appendix for trusted reviewers, with sensitive details "
    "redacted."
))

# 5. Taxonomy
story.append(P("5. Taxonomy of Recoverable Behavioral Failures", h1))
story.append(P(
    "The taxonomy is layered by failure locus. Locus separation matters because not every "
    "user-visible failure should be attributed to the model core. Some failures arise in "
    "retrieval policy; some in batch-effort allocation; some in artifact generation; some in "
    "client transport; some in product memory; some in the evaluation pipeline itself. A "
    "useful framework should locate the failure precisely enough to guide the right mitigation."
))

story.append(P("5.0 A note on mode overlap and granularity", h2))
story.append(P(
    "Sixteen modes is a deliberate choice. Several pairs of modes are clearly adjacent and "
    "could in principle be collapsed: PTS and SMI are both retrieval-policy failures; MRT, UCT, "
    "and MSI are all interruption-style failures at different loci; AFF and EBC are both "
    "artifact-side failures. We keep them separate in this taxonomy for three reasons. First, "
    "the <i>mitigation</i> implied by each mode is different (escalation policy versus "
    "consistency policy; resume-state preservation versus rate-limit handling; readiness audit "
    "versus boundary audit); collapsing the codes would obscure the mitigation taxonomy. "
    "Second, the <i>locus</i> attribution is different across the apparent pairs (model "
    "retrieval policy versus client transport versus rate limiter); collapsing them would "
    "obscure where instrumentation is needed. Third, an empirically-driven collapse should "
    "follow from data: once cross-model and cross-user data accumulates, modes that always "
    "co-occur in the same items can be merged with reviewer confidence, while modes that "
    "dissociate empirically should stay separate. The present taxonomy is therefore offered as "
    "a starting partition for measurement, not as a final structural claim."
))

rows = [
    ["Code", "Name", "Primary locus", "User-visible cost"],
    ["PTS",  "Premature Termination of Search",      "Model / retrieval policy",          "False unresolved answers; missed information"],
    ["BDTF", "Breadth-Depth Tradeoff Failure",       "Model policy under batch load",     "Shallow per-item analysis presented as complete coverage"],
    ["SMI",  "Search Methodology Inconsistency",     "Retrieval strategy",                "Inconsistent escalation across similar subtasks"],
    ["MRT",  "Mid-Response Truncation",              "Infrastructure / model interaction","Partial output, lost progress, incomplete generation"],
    ["MSI",  "Mobile Streaming Interruption",        "Client / transport",                "Dropped response on screen-lock or mobile interruption"],
    ["FPG",  "Feedback Persistence Gap",             "Product / training pipeline",       "Same corrections not preserved across sessions"],
    ["RFI",  "Retry-Failure Invisibility",           "Evaluation pipeline",               "Offline review cannot distinguish cannot-solve from did-not-try"],
    ["STK",  "Stale Third-Party Tool/UI Knowledge",  "Model knowledge / tool guidance",   "Confident instructions for changed live interfaces"],
    ["QI",   "Quantitative Inconsistency",           "Reasoning / self-audit",            "Contradictory numbers within one response"],
    ["PPG",  "Phantom Placeholder Persistence",      "Artifact / code generation",        "Template placeholders emitted as executable commands"],
    ["UCT",  "Usage-Cap Termination",                "System / rate limit",               "Mid-task interruption and degraded resume state"],
    ["VMC",  "Visual Misreading Cascade",            "Multimodal interpretation",         "Repeated confident misreadings of structured visual input"],
    ["AFF",  "Artifact Finalization Failure",        "Artifact generation",               "File exists but is incomplete, poorly formatted, or not apply-ready"],
    ["SVD",  "Source Verification Drift",            "Citation / retrieval practice",     "Claims or links not sufficiently verified against source"],
    ["EBC",  "Editorial Boundary Contamination",     "Artifact boundary management",      "Process notes, ratings, or strategy inserted into publishable artifact"],
    ["ACM",  "Audience / Context Miscalibration",    "Communication / register",          "Technically correct content unsafe or off-register for the intended audience"],
]
story.append(make_table(rows, [0.55*inch, 2.05*inch, 1.65*inch, 2.65*inch]))
story.append(P("Table 3. Layered taxonomy of observed and proposed recoverable behavioral failure modes.", caption))


# ---- Mode sections sourced from mode_content ----
for i, m in enumerate(MODES, start=1):
    story.append(P(f"5.{i} {m['name']} ({m['code']})", h2))
    story.append(P(f"<b>Definition.</b> {m['definition']}"))
    story.append(P(f"<b>Observed pattern.</b> {m['observed']}"))
    story.append(P(f"<b>Why it matters.</b> {m['why']}"))
    story.append(P(f"<b>Differentiation.</b> {m['differentiation']}"))
    story.append(P(f"<b>Detection.</b> {m['detection']}"))
    story.append(P(f"<b>Mitigation.</b> {m['mitigation']}"))

# 6. Cross-Workflow Observations
story.append(P("6. Cross-Workflow Observations", h1))

story.append(P("6.1 Document-generation and artifact-production workflows", h2))
story.append(P(
    "When the deliverable is a document, slide deck, spreadsheet, or code file, terminal text "
    "quality is necessary but not sufficient. The artifact must open cleanly, render correctly, "
    "and meet the user's apply-ready criteria. AFF, PPG, and EBC are concentrated in these "
    "workflows; their incidence becomes visible only when the artifact is evaluated outside the "
    "chat. A reasonable evaluation discipline treats the artifact, not the response describing "
    "the artifact, as the primary unit of measurement."
))

story.append(P("6.2 Source-verification and multi-step research workflows", h2))
story.append(P(
    "Citation-heavy and verification-heavy workflows surface SVD, PTS, and SMI together. The "
    "model may begin with disciplined source-grounding, drift into plausible synthesis as the "
    "task lengthens, and selectively escalate retrieval on some claims but not others. "
    "Claim-level verification checks are the appropriate measurement; citation presence alone "
    "is insufficient."
))

story.append(P("6.3 Public-communication and audience-targeted workflows", h2))
story.append(P(
    "When an artifact is intended for a public or restricted audience, ACM and EBC become "
    "salient. Technically correct content can leak private context, off-register tone, or "
    "advisory metadata. Mitigation is policy-level rather than model-capability-level: "
    "explicit audience framing in the prompt or system instruction, combined with a "
    "pre-delivery audit for boundary contamination."
))

story.append(P("6.4 Quantitative reasoning workflows", h2))
story.append(P(
    "QI surfaces most often when responses contain multiple quantitative claims under shared "
    "assumptions. The detection method is mechanical (intra-response arithmetic check) and is "
    "currently underused. Quantitative consistency is well-suited to deterministic automated "
    "checks, which makes it an attractive first target for benchmark inclusion."
))

# 7. Pilot Experiment
story.append(PageBreak())
story.append(P("7. Pilot Experiment: Retry-Probe Quantification of PTS", h1))
story.append(P("7.1 Setup", h2))
story.append(P(
    "The primary measured case is a fifteen-item heterogeneous retrieval task. Each item "
    "requires retrieval, interpretation, and structured per-item output. Items belong to three "
    "structural classes: (1) direct URLs with human-readable paths (n=9); (2) URLs containing "
    "opaque numeric identifiers requiring secondary lookup to extract title or content (n=3); "
    "(3) title-only references requiring search (n=3). The first pass is evaluated as "
    "successful if the model produces a substantive resolution. The retry pass is evaluated "
    "under the same criterion after a standardized user-prompted retry that supplies no new "
    "substantive information."
))

story.append(P("7.2 Procedure", h2))
story.append(P(
    "For each item, two binary outcomes were recorded from the verbatim session transcript: "
    "(i) first-pass success, and (ii) success after a single standardized retry of the form "
    "'try a different approach.' The retry prompt did not supply new documents, new tools, or "
    "new task information. Coding was conservative: an item was counted as a recoverable "
    "behavioral failure only when the second-pass success demonstrated a previously available "
    "capability rather than newly supplied information."
))

story.append(P("7.3 Results", h2))
rows = [
    ["Metric", "Value", "95% CI"],
    ["Total items (N)",                                              "15",                  "&mdash;"],
    ["First-pass resolved (<i>p</i><sub>1</sub>)",                   "12 / 15 = 80.0%",     "Wilson: [54.8%, 93.0%]"],
    ["Resolved after retry (<i>p</i><sub>r</sub>)",                  "15 / 15 = 100.0%",    "Wilson: [79.6%, 100.0%]"],
    ["Recoverable first-pass failures",                              "3 / 15 = 20.0%",      "Wilson: [7.0%, 45.2%]"],
    ["Recoverability gap (<i>p</i><sub>r</sub> - <i>p</i><sub>1</sub>)", "+20.0 pp",         "Discordant-proportion CI: [7.0%, 45.2%]"],
]
story.append(make_table(rows, [2.55*inch, 1.7*inch, 2.6*inch]))
story.append(P("Table 4. Retry-probe pilot results with Wilson 95% confidence intervals.", caption))

rows = [
    ["Item structural class", "n", "First-pass resolved", "First-pass rate", "Recoverable failures"],
    ["Direct URL (human-readable path)",       "9",  "9",  "100%", "0"],
    ["URL with opaque numeric identifier",     "3",  "0",  "0%",   "3"],
    ["Title-only (search-required)",           "3",  "3",  "100%", "0"],
]
story.append(make_table(rows, [2.6*inch, 0.45*inch, 1.45*inch, 1.15*inch, 1.25*inch]))
story.append(P("Table 5. Pilot first-pass performance by item structural class.", caption))

story.append(P("7.4 Exact small-sample statistical analysis", h2))
story.append(P(
    "The recoverable-failure rate is 3 / 15 = 20.0%, with Wilson 95% confidence interval "
    "[7.0%, 45.2%]. The width of the interval reflects the small sample. The structural-class "
    "association is striking: 0 of 3 opaque-identifier items resolved on first pass; 12 of 12 "
    "non-opaque items resolved on first pass."
))
rows = [
    ["", "First-pass success", "First-pass failure", "Row total"],
    ["Opaque-identifier",      "0",  "3", "3"],
    ["Non-opaque",             "12", "0", "12"],
    ["Column total",           "12", "3", "15"],
]
story.append(make_table(rows, [1.85*inch, 1.7*inch, 1.7*inch, 1.05*inch]))
story.append(P("Table 6. Contingency table for first-pass success by item structural class.", caption))

story.append(P(
    "A two-sided Fisher exact test on the 2 by 2 contingency table yields <i>p</i> = 0.0022. "
    "The one-sided test for the hypothesis that opaque-identifier items have lower first-pass "
    "success also yields <i>p</i> = 0.0022. The result is statistically meaningful for this "
    "item set but should not be read as a population-level rate. The item set was not randomly "
    "sampled from a defined universe; it is a single heterogeneous batch from a naturalistic "
    "workflow."
))

story.append(P("7.5 What the pilot supports and does not support", h2))
story.append(Bul("It supports the <b>existence</b> of recoverable behavioral failures in at least one measured retrieval workflow."))
story.append(Bul("It supports treating first-pass and retry-after-prompt success as separately measurable quantities."))
story.append(Bul("It suggests, exploratorily, that opaque numeric identifiers may be a high-incidence trigger for PTS under batch load."))
story.append(Bul("It does <b>not</b> establish a population-level PTS rate for any model or vendor."))
story.append(Bul("It does <b>not</b> establish a universal opaque-identifier-to-failure relationship."))
story.append(Bul("It does <b>not</b> establish a model ranking, because workload and model identity are not experimentally balanced."))

# 8. Observational Notes
story.append(P("8. Observational Notes Beyond the Pilot", h1))
story.append(P(
    "Beyond the measured PTS pilot, the case-study corpus contains transcript-verifiable "
    "instances of additional modes. These are reported at the level of pattern, trigger, and "
    "recovery so that they can be probed in controlled replication. No additional rates are "
    "claimed for these modes; they are Tier 2 observations supporting taxonomy and protocol "
    "design rather than quantitative results. The corpus includes instances of STK (multi-turn "
    "navigation of a third-party developer console with stale UI descriptions), QI (single-"
    "response analytic output with internally inconsistent numeric claims), PPG (shell commands "
    "containing literal placeholders the surrounding context resolved), VMC (sequential "
    "confident misreadings of a structured visual document), UCT (cap-driven terminations "
    "followed by malformed continuation completions), and BDTF (uniform shallow per-item "
    "dispositions under multi-item batches)."
))

# 9. Protocol
story.append(P("9. Proposed Multi-Model Evaluation Protocol", h1))
story.append(P(
    "This section specifies a controlled multi-model benchmark designed to break the model-task "
    "confounds described in &sect;4.4 and to test the modes catalogued in &sect;5. The protocol "
    "is grounded in an accompanying ten-task evaluation pack covering five task categories. "
    "Results from running this protocol are not yet available; the protocol is described as a "
    "<b>planned replication</b>, not a completed study."
))

story.append(P("9.1 Task families", h2))
rows = [
    ["Family", "Modes targeted", "Example measurement"],
    ["Retrieval retry probes",              "PTS, SMI",       "First-pass vs. retry success on direct, opaque-ID, and title-only items"],
    ["Batch retrieval and scaling",         "BDTF",           "Per-item correctness as batch size increases from 1 to 30"],
    ["Quantitative consistency",            "QI",             "Internal arithmetic consistency in responses with multiple numerical claims"],
    ["Structured visual interpretation",    "VMC",            "Field-extraction accuracy before downstream interpretation"],
    ["Third-party UI / tool instructions",  "STK",            "Accuracy and staleness framing for fast-changing tool instructions"],
    ["Phantom placeholders",                "PPG",            "Placeholder leakage rate in code and command outputs"],
    ["Artifact finalization and delivery",  "AFF, PPG, EBC",  "Downloadability, formatting, placeholder absence, boundary cleanliness"],
    ["Editorial boundary contamination",    "EBC",            "Absence of process commentary in publishable artifacts"],
    ["Audience / context calibration",      "ACM",            "Absence of off-register or boundary-inappropriate content"],
]
story.append(make_table(rows, [2.0*inch, 1.4*inch, 3.45*inch]))
story.append(P("Table 7. Task families in the proposed multi-model evaluation protocol.", caption))

story.append(P("9.2 Model coverage", h2))
story.append(P(
    "The protocol is designed for parallel administration across frontier model families. "
    "Concrete targets include but are not limited to the Claude family (Sonnet, Opus), the GPT "
    "family, the Gemini family, and any additional frontier model an investigator can access. "
    "The pilot pack scaffolding supports the three named API surfaces and is extensible. The "
    "objective is to administer matched tasks under standardized prompts, retry prompts, tool "
    "access, and decoding settings, so that any observed differences across models are "
    "attributable to model identity rather than to task or prompt heterogeneity."
))

story.append(P("9.3 Metrics", h2))
rows = [
    ["Metric", "Definition", "Applies to"],
    ["First-pass success",          "Proportion solved without retry",                              "All task families"],
    ["Retry success",               "Proportion solved after standardized retry",                   "All recoverability probes"],
    ["Recoverability gap",          "Retry success minus first-pass success",                       "PTS, BDTF, VMC, AFF"],
    ["Artifact-readiness rate",     "Deliverables passing objective file and formatting checks",    "PDF / DOCX / slides / spreadsheets / code"],
    ["Numeric consistency rate",    "Proportion of multi-numeric responses passing intra-response audit", "Quantitative tasks"],
    ["Placeholder leakage rate",    "Proportion of code/command outputs containing unresolved placeholders","Code and command-generation tasks"],
    ["Boundary-contamination rate", "Artifacts containing process notes, ratings, or chat-only content", "Publication and public-communication artifacts"],
    ["Verification compliance rate","Proportion of items where stated verification was performed",  "Verification-requiring tasks"],
    ["Claim-source support rate",   "Claims supported by cited sources at the required specificity","Research and citation tasks"],
    ["Human intervention cost",     "Number of corrective turns to reach acceptable output",        "All workflow tasks"],
]
story.append(make_table(rows, [1.85*inch, 3.0*inch, 1.95*inch]))
story.append(P("Table 8. Metrics for the proposed multi-model evaluation protocol.", caption))

story.append(P("9.4 Procedure", h2))
story.append(N(1, "<b>Item construction.</b> For retrieval, construct a balanced item set: 20 direct URLs, 20 opaque-identifier URLs, 20 title-only references."))
story.append(N(2, "<b>Prompt standardization.</b> Each model receives the same initial prompt and, for recoverability probes, the same standardized retry prompt."))
story.append(N(3, "<b>Tool and setting standardization.</b> Tool access, temperature, max-tokens, and system-prompt content held constant across models within a family of items."))
story.append(N(4, "<b>Batch design.</b> Retrieval items administered at N = 1, 5, 15, 30 to support batch-scaling analysis."))
story.append(N(5, "<b>Annotation.</b> Each item double-coded by independent annotators. Inter-annotator agreement reported using Cohen's kappa or Krippendorff's alpha."))
story.append(N(6, "<b>Reporting.</b> Confidence intervals for all rates. Exact tests for small-sample comparisons."))

story.append(P("9.5 Sample size and power", h2))
story.append(P(
    "The pilot's N = 15 yields wide confidence intervals. A benchmark intended to estimate "
    "recoverability rates with narrower intervals should size each condition accordingly. For "
    "a binary failure rate near 20% with desired margin of error +/- 5 percentage points at "
    "95% confidence, roughly 250 items per condition are required; for +/- 3 points roughly "
    "700; for +/- 2 points roughly 1500. Detection of a 10-percentage-point across-model "
    "difference at 80% power requires approximately 200 items per arm under comparable rates."
))

# 10. Mitigation
story.append(P("10. Mitigation Implications", h1))
story.append(P(
    "The taxonomy suggests practical, low-cost mitigations that do not require new model "
    "capabilities. They require improved execution policy, product affordances, and evaluation "
    "criteria. The mitigations below map directly to the modes in &sect;5."
))
story.append(Bul("<b>Explicit escalation policy</b> for retrieval (PTS, SMI)."))
story.append(Bul("<b>Batch-aware effort budgeting</b> with per-item verification flags (BDTF)."))
story.append(Bul("<b>Self-verification gates</b>: arithmetic checks (QI), claim-source entailment (SVD), file-readiness checks (AFF, PPG)."))
story.append(Bul("<b>Visual-input verification loop</b> (VMC)."))
story.append(Bul("<b>Staleness-aware tool guidance</b> (STK)."))
story.append(Bul("<b>Pre-delivery boundary audit</b> (EBC); audience-and-channel checks (ACM)."))
story.append(Bul("<b>Graceful resume design</b> across interruptions (MRT, UCT, MSI)."))
story.append(Bul("<b>Counterfactual-replay evaluation</b> (RFI)."))

# 11. Limitations
story.append(P("11. Limitations and Threats to Validity", h1))
story.append(N(1, "<b>Single-user evidence base.</b> Fourteen sessions from a single user. Generalization requires multi-user replication."))
story.append(N(2, "<b>Single-coder bias.</b> Future work includes a double-coded reliability subsample with reported Cohen's kappa."))
story.append(N(3, "<b>Inductive taxonomy.</b> Sixteen modes may be incomplete; some may collapse empirically (see &sect;5.0 for rationale)."))
story.append(N(4, "<b>Model self-report uncertainty.</b> Mechanism descriptions that rest on model self-reports are treated as suggestive."))
story.append(N(5, "<b>Missing per-message model attribution</b> in the Claude.ai export schema."))
story.append(N(6, "<b>Model-task confound.</b> Case-study task type and model identity are partially correlated; the multi-model protocol is the appropriate vehicle for clean comparison."))
story.append(N(7, "<b>Single-batch quantitative anchor.</b> Section 7 reports one batch with wide confidence intervals."))
story.append(N(8, "<b>Selective observability.</b> Failures are easier to detect when users are expert enough to challenge outputs."))
story.append(N(9, "<b>Cross-platform abstractions are summary-level.</b> Replication should include explicit task logs."))

# 12. Future Work
story.append(P("12. Future Work", h1))
story.append(N(1, "Run the &sect;9 multi-model protocol across Claude, GPT, Gemini, and additional frontier model families."))
story.append(N(2, "Expand to a multi-user corpus with double-coding and reported kappa."))
story.append(N(3, "Longitudinal tracking across major model-version releases."))
story.append(N(4, "Artifact-evaluation infrastructure for downloadability, formatting, placeholder absence, link freshness, boundary contamination."))
story.append(N(5, "Recommendation to AI providers: include a model field on each message in conversation-export schemas."))
story.append(N(6, "Behavioral-failure capture in product feedback flows."))

# 13. Conclusion
story.append(P("13. Conclusion", h1))
story.append(P(
    "Recoverable behavioral failures are cases where a model appears capable of completing a "
    "task but fails to exercise that capability on the first pass. They are not captured by "
    "standard terminal-output evaluation, because they become visible only when a retry, "
    "correction, or artifact audit reveals that the model could have produced the correct "
    "output without new substantive information. This paper contributes a definition, a "
    "layered sixteen-mode taxonomy, a quantitative retry-probe pilot with exploratory "
    "confidence intervals and an exact small-sample association test, abstracted cross-"
    "platform observations of artifact-readiness and editorial-boundary modes, and a multi-"
    "model evaluation protocol grounded in a ten-task pilot pack and supporting analysis "
    "scripts. The central implication is that AI evaluation should measure not only "
    "capability but also persistence, verification, escalation, artifact readiness, and "
    "boundary control."
))

# References
story.append(P("References", h1))
refs = [
    "Bai, Y., Jones, A., Ndousse, K., Askell, A., Chen, A., DasSarma, N., et al. (2022). Training a helpful and harmless assistant with reinforcement learning from human feedback. <i>arXiv:2204.05862</i>.",
    "Chen, W., Wang, X., &amp; Wang, W. Y. (2021). A dataset for answering time-sensitive questions. <i>arXiv:2108.06314</i>.",
    "Christiano, P. F., Leike, J., Brown, T., Martic, M., Legg, S., &amp; Amodei, D. (2017). Deep reinforcement learning from human preferences. <i>NeurIPS</i>.",
    "Hendrycks, D., Burns, C., Basart, S., Zou, A., Mazeika, M., Song, D., &amp; Steinhardt, J. (2021). Measuring massive multitask language understanding (MMLU). <i>ICLR</i>.",
    "Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., &amp; Narasimhan, K. (2024). SWE-bench: Can language models resolve real-world GitHub issues? <i>ICLR</i>.",
    "Liang, P., Bommasani, R., Lee, T., Tsipras, D., Soylu, D., Yasunaga, M., et al. (2022). Holistic evaluation of language models (HELM). <i>arXiv:2211.09110</i>.",
    "Lin, S., Hilton, J., &amp; Evans, O. (2022). TruthfulQA: Measuring how models mimic human falsehoods. <i>ACL</i>.",
    "Liska, A., Kocisky, T., Gribovskaya, E., Terzi, T., Sezener, E., Agrawal, D., et al. (2022). StreamingQA: A benchmark for adaptation to new knowledge over time. <i>ICML</i>.",
    "Park, P. S., Goldstein, S., O'Gara, A., Chen, M., &amp; Hendrycks, D. (2024). AI deception: A survey of examples, risks, and potential solutions. <i>Patterns</i>, 5(5).",
    "Sharma, M., Tong, M., Korbak, T., Duvenaud, D., Askell, A., Bowman, S. R., et al. (2023). Towards understanding sycophancy in language models. <i>arXiv:2310.13548</i>.",
    "Srivastava, A., Rastogi, A., Rao, A., Shoeb, A. A. M., Abid, A., Fisch, A., et al. (2023). Beyond the imitation game (BIG-Bench). <i>TMLR</i>.",
    "Yin, R. K. (2018). <i>Case Study Research and Applications: Design and Methods</i> (6th ed.). SAGE.",
    "Zhou, S., Xu, F. F., Zhu, H., Zhou, X., Lo, R., Sridhar, A., et al. (2024). WebArena: A realistic web environment for building autonomous agents. <i>ICLR</i>.",
]
for r in refs:
    story.append(Bul(r))

# Appendices
story.append(PageBreak())
story.append(P("Appendix A. Observation Bank Coding Schema", h1))
rows = [
    ["Field", "Description"],
    ["observation_id",                "Stable identifier"],
    ["task_family",                   "Retrieval, artifact, visual, quantitative, UI/tool, source-grounding, other"],
    ["original_prompt",               "User request (abstracted where needed for privacy)"],
    ["first_pass_output",             "Model response or artifact outcome on the first attempt"],
    ["failure_criterion",             "Reason the first-pass output is judged a failure"],
    ["retry_prompt",                  "Standardized retry used to test recoverability"],
    ["new_information_introduced",    "Yes / No; if Yes, item is excluded from RBF"],
    ["post_retry_output",             "Second-pass result"],
    ["mode_code",                     "One of the 16 codes in Table 3"],
    ["trigger",                       "Observed condition under which the failure occurred"],
    ["recovery_type",                 "Search escalation / verification / structural confirmation / boundary audit / other"],
    ["user_visible_cost",             "Time, confusion, unusable artifact, missed information, rework"],
    ["evidence_tier",                 "Tier 1 / 2 / 3 / 4 per &sect;4.2"],
]
story.append(make_table(rows, [1.85*inch, 4.45*inch]))
story.append(P("Table A1. Observation-bank coding schema.", caption))

story.append(P("Appendix B. Experiment Pack and Task Schema", h1))
story.append(P(
    "The accompanying experiment pack provides a small pilot benchmark and runner scaffold for "
    "measuring recoverable-behavioral-failure proxies across multiple LLM APIs. It contains ten "
    "items distributed across five categories, plus runner and scorer scripts that administer "
    "the items against OpenAI, Anthropic, and Google API surfaces."
))
rows = [
    ["Category", "n", "Purpose"],
    ["QI",          "2", "Internal numerical consistency on responses with multiple quantitative claims"],
    ["PPG",         "2", "Placeholder leakage in code or shell-command outputs"],
    ["EBC",         "2", "Absence of process commentary in publication-style outputs"],
    ["ACM",         "2", "Audience appropriateness in public-summary outputs"],
    ["RETRY_PROXY", "2", "Stated retry strategy for retrievals returning thin or empty results"],
]
story.append(make_table(rows, [1.5*inch, 0.45*inch, 4.35*inch]))
story.append(P("Table B1. Categories in the v1.0 experiment pack.", caption))

story.append(P("Appendix C. Annotation Rubric", h1))
story.append(N(1, "Did the first-pass output satisfy the task's acceptance criteria? If yes, label <i>first-pass success</i>."))
story.append(N(2, "If the first-pass output failed, did the retry succeed?"))
story.append(N(3, "Did the retry prompt introduce new substantive information? If yes, label <i>ordinary interactive correction</i>."))
story.append(N(4, "If the retry succeeded without new information, label <i>recoverable behavioral failure</i> and assign a mode code."))
story.append(N(5, "If the retry also failed, label <i>non-recoverable under available context</i>."))
story.append(N(6, "If determination is unclear, label <i>ambiguous</i>."))

story.append(P("Appendix D. Reproducibility Checklist", h1))
story.append(Bul("Item set with stable IDs, task-family labels, prompts, retry prompts, expected outputs, verification methods."))
story.append(Bul("Model and tool settings recorded: model name, temperature, max-tokens, system prompt, tool list, decoding settings."))
story.append(Bul("Raw outputs archived in append-only JSONL with timestamps."))
story.append(Bul("Automated checks distributed as a separate scorer script."))
story.append(Bul("Annotation guidelines and double-coded labels released with kappa or alpha reported."))
story.append(Bul("Analysis notebook producing all tables, confidence intervals, statistical tests."))
story.append(Bul("Data statement describing collection method, privacy controls, redaction procedures, licenses."))
story.append(Bul("Versioning: pack version, model versions, analysis-notebook commit hash recorded in the results file."))


# ---------- build with multiBuild for TOC ----------
doc = MyDocTemplate(
    OUTPUT, pagesize=letter,
    leftMargin=0.85*inch, rightMargin=0.85*inch,
    topMargin=0.85*inch, bottomMargin=0.85*inch,
    title="Observed Recoverable Behavioral Failure Modes in LLM Workflows (v1.8)",
    author="Vijay Suresh",
)
doc.multiBuild(story)
print(f"Wrote {OUTPUT}")
