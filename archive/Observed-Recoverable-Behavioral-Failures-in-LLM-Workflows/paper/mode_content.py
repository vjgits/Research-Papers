"""Single source of truth for the 16 mode treatments in §5 of the v1.8 paper.

Each entry has six fields matching the v1.7 structure: definition, observed
pattern, why it matters, differentiation from adjacent modes, detection method,
and mitigation implication. Content depth is calibrated to v1.7: roughly
6 paragraphs of substantive multi-sentence prose, averaging ~1400 chars per
mode. Both the reportlab generator and the LaTeX generator import from here
so they stay in sync.
"""

MODES = [
    {
        "code": "PTS",
        "name": "Premature Termination of Search",
        "definition": (
            "The model declares an information item unresolved after a small number of retrieval "
            "attempts, even though a readily available alternative retrieval strategy would resolve it. "
            "The first attempt typically uses a thin or generic query construction; the second attempt, "
            "issued under a retry prompt that introduces no new information, succeeds."
        ),
        "observed": (
            "In the pilot retrieval task, three items whose URLs contained opaque numeric identifiers "
            "were marked unresolved on the first pass after generic keyword queries returned thin "
            "results. After a standardized retry prompt the model used site-targeted query construction "
            "and resolved all three. The capability gap on the first pass was therefore a "
            "query-construction policy decision rather than a knowledge or tool limit."
        ),
        "why": (
            "PTS is among the most consequential modes because it masquerades as missing knowledge. "
            "The user receives an &lsquo;unknown&rsquo; response and reasonably treats it as a "
            "capability boundary. In fact the system has not exhausted available retrieval policy. "
            "The cost is paid both as missed information and as user-side supervisory load: the user "
            "must recognize that the response is recoverable and issue the retry themselves."
        ),
        "differentiation": (
            "PTS is distinct from <b>SMI</b> (which concerns inconsistency across similar subtasks "
            "rather than premature stopping on one subtask) and from <b>RFI</b> (which is the "
            "evaluation-pipeline blind spot that makes PTS invisible in offline review). PTS is also "
            "distinct from genuine retrieval failure where no alternative strategy would help; the "
            "diagnostic for PTS is that an alternative strategy demonstrably exists."
        ),
        "detection": (
            "Retry probes constructed so that the first-pass query is likely to be thin but at least "
            "one alternative strategy is known to succeed. Measure first-pass success and "
            "retry-after-prompt success separately; the gap quantifies PTS. Probe construction "
            "recipes include items with opaque-identifier URLs, items whose canonical answer is on a "
            "specific known site, and items that require an exact-string match the generic query "
            "would dilute."
        ),
        "mitigation": (
            "An explicit retrieval escalation policy: when the first search returns thin, the model "
            "should systematically try query rewriting, site restriction, exact-string identifier "
            "search, and source triangulation before declaring failure. The escalation should be "
            "visible to the user so that supervision is calibrated rather than always assumed; this "
            "also helps the user trust the &lsquo;unknown&rsquo; verdicts that remain after escalation."
        ),
    },
    {
        "code": "BDTF",
        "name": "Breadth-Depth Tradeoff Failure",
        "definition": (
            "When presented with a large batch, the model implicitly optimizes for covering all items "
            "rather than verifying each item deeply. The result is a superficially complete response "
            "with weak per-item grounding: every item appears addressed, but per-item depth degrades "
            "as the batch size grows."
        ),
        "observed": (
            "Multi-item evaluation tasks elicit short, uniform dispositions even when individual items "
            "differ materially in difficulty. Items requiring secondary lookup are sometimes resolved "
            "without the lookup having occurred. Items requiring verification are sometimes presented "
            "with confident framings derived from partial reads. The user infers uniform depth from "
            "uniform output length, which is exactly the inference the model has not earned."
        ),
        "why": (
            "BDTF is an allocation error in which the appearance of coverage substitutes for "
            "verification. The user reads a list, sees that every item has been addressed, and "
            "reasonably assumes uniform depth. Without explicit depth indicators the user is forced "
            "to re-verify each item to recover trust&mdash;at which point the breadth advantage of "
            "the batch was illusory and the depth cost has merely shifted."
        ),
        "differentiation": (
            "BDTF differs from <b>MRT</b> (which is truncation within a single response) and from "
            "<b>PTS</b> (which is premature stopping on a single retrieval). BDTF is a batch-level "
            "allocation phenomenon: per-item correctness degrades as N grows even when per-item "
            "tasks at small N are reliably solved. It can co-occur with PTS but is operationally "
            "separable through batch-size variation."
        ),
        "detection": (
            "Batch-scaling curves: administer the same items at batch sizes N = 1, 5, 15, 30. "
            "Measure per-item correctness against N. The slope quantifies BDTF; the inflection "
            "point identifies the effective batch capacity. A healthy policy under load surfaces "
            "verification depth per item rather than hiding allocation behind uniform output length."
        ),
        "mitigation": (
            "Batch-aware effort budgeting: for large batches, the model should state per-item "
            "uncertainty, allocate verification depth, and surface items that received only "
            "shallow processing. A simple product affordance is per-item flags that distinguish "
            "&lsquo;verified,&rsquo; &lsquo;partially verified,&rsquo; and &lsquo;not verified&rsquo; "
            "outputs."
        ),
    },
    {
        "code": "SMI",
        "name": "Search Methodology Inconsistency",
        "definition": (
            "The model uses stronger retrieval tactics for some items and weaker tactics for similar "
            "items within the same session, with no explicit reason for the difference. Query "
            "construction varies between generic keyword search, site-targeted search, and "
            "identifier-anchored search without a stated escalation rule."
        ),
        "observed": (
            "Across a batch of retrieval subtasks, items that would have benefited from the stronger "
            "tactic receive the weaker tactic; users notice the inconsistency only when they observe "
            "that one item succeeded under exactly the strategy that was not applied to a similar "
            "item. The same model can exhibit PTS on one item, escalate appropriately on a similar "
            "item, and fail to apply the same escalation to a third."
        ),
        "why": (
            "Inconsistent retrieval discipline shifts the burden of escalation onto the user. A "
            "robust workflow expects a predictable escalation protocol on thin first results: query "
            "rewriting, site restriction, identifier search, title extraction, source triangulation. "
            "SMI occurs when this escalation is selectively applied, so the user cannot rely on "
            "uniform retrieval policy and must monitor strategy choice item by item."
        ),
        "differentiation": (
            "PTS is a failure mode within a subtask; SMI is a consistency mode across subtasks. The "
            "two can co-occur but are operationally separable: SMI persists even when overall PTS "
            "incidence is low, because the issue is the conditional probability of strategy "
            "escalation given a thin first result, not the absolute incidence of premature stopping."
        ),
        "detection": (
            "Per-subtask query logging within a session. Compute (a) the distribution of "
            "queries-per-subtask, (b) the distribution of query-construction strategies, and (c) "
            "the conditional probability of switching strategy given a thin first result. A healthy "
            "retrieval policy should exhibit consistent escalation across structurally similar "
            "subtasks."
        ),
        "mitigation": (
            "A documented escalation protocol applied uniformly across retrieval subtasks. Internal "
            "logging that exposes the chosen strategy to evaluators and, where appropriate, to the "
            "user, so that inconsistencies are noticeable rather than hidden. Consistency is itself "
            "a user-trust signal even when the underlying strategy is imperfect."
        ),
    },
    {
        "code": "MRT",
        "name": "Mid-Response Truncation",
        "definition": (
            "The model begins generating a response, makes partial progress, and the stream "
            "terminates before completion, often after partial tool use or partial drafting. The "
            "termination is signaled by a generic error rather than a graceful wind-down."
        ),
        "observed": (
            "Long multi-part responses on heterogeneous batches sometimes terminate with a generic "
            "recovery message. Partial work is not always preserved or replayable. The user is "
            "required to issue a fresh prompt to resume, with no native carry-over of intermediate "
            "state. In long workflows the cost of lost intermediate progress compounds: each "
            "truncation imposes recovery work proportional to task complexity."
        ),
        "why": (
            "MRT is costly not only because the answer is incomplete but because the partial work "
            "may need to be reassembled manually. The user must reconstruct what the model had "
            "already done, decide what to keep, and re-prompt for the remainder. The cost scales "
            "with response length and tool-call density&mdash;exactly the regime where users were "
            "relying on the model to reduce supervisory load."
        ),
        "differentiation": (
            "MRT is an infrastructure-side termination of a single response; <b>UCT</b> is a "
            "system-level rate-limit termination of the conversation; <b>MSI</b> is a "
            "client-side stream drop. All three share the user-visible appearance of an "
            "interrupted task but differ in locus, signal, and recovery behavior."
        ),
        "detection": (
            "Near-budget telemetry: log the fraction of token, tool-call, or wall-clock budget "
            "consumed at response termination. For a healthy generator, the distribution should be "
            "bimodal&mdash;very early when the task is short, well below threshold when the model "
            "voluntarily concluded. A spike of terminations at or near the budget boundary indicates "
            "MRT."
        ),
        "mitigation": (
            "A structured progress ledger that allows the model and the system to preserve and "
            "resume intermediate state when generation fails. Resume-state checkpoints during long "
            "generations, with the option to surface and replay partial outputs. Where graceful "
            "termination is feasible, the model should be cued to summarize completed work before "
            "the budget is exhausted."
        ),
    },
    {
        "code": "MSI",
        "name": "Mobile Streaming Interruption",
        "definition": (
            "Mobile or client-side interruptions can drop an in-progress streaming response, with no "
            "recovery of the partial output when the user returns to the session. Screen-lock, "
            "backgrounding, and connection drops on mobile clients are common triggers."
        ),
        "observed": (
            "Screen-lock during streaming generation on mobile clients sometimes terminates the "
            "connection. The session reopens without the partial response surfaced. Users describe "
            "the failure as workflow unreliability rather than as a model error&mdash;they may not "
            "know whether the model finished and the partial output was lost in transit, or whether "
            "the model itself never finished."
        ),
        "why": (
            "Long AI workflows increasingly depend on streaming responses. When the client loses "
            "partial output, the cost is workflow-level: the user must re-issue the request and "
            "absorb the full latency again. The failure compounds with MRT and UCT to make long "
            "sessions on mobile materially less reliable than on desktop."
        ),
        "differentiation": (
            "MSI is client/transport-layer; MRT is infrastructure/model-side; UCT is system "
            "rate-limit. All three are recoverable in principle through different mechanisms&mdash;"
            "client-side buffering for MSI, server-side resume for MRT, graceful continuation for "
            "UCT&mdash;but the locus determines the correct mitigation."
        ),
        "detection": (
            "Client-side telemetry on stream-drop events correlated with foreground/background "
            "lifecycle and with screen-lock events. The relevant rate is interrupted streams per "
            "long-generation request on mobile clients, segmented by client version and connection "
            "type."
        ),
        "mitigation": (
            "Persistent server-side response buffering with client reattachment on resume, so a "
            "screen-lock event does not erase work already produced. Notification surfaces that "
            "allow the user to recover the interrupted response on next session open, with the "
            "partial output highlighted so the user can decide whether to continue or restart."
        ),
    },
    {
        "code": "FPG",
        "name": "Feedback Persistence Gap",
        "definition": (
            "Within-session corrections, scope clarifications, and explicit user preferences do not "
            "persist beyond the session unless an explicit memory surface or product mechanism "
            "captures them. The same user encounters the same correctable issue in subsequent "
            "sessions."
        ),
        "observed": (
            "A user corrects a stylistic or factual error in one session; the same error recurs in "
            "subsequent sessions without the correction being applied. Aggregate signal from "
            "preference data eventually reaches model training, but individual users observe no "
            "compounding return on their corrective effort across sessions."
        ),
        "why": (
            "FPG is not always a defect; user control and privacy require limits on cross-session "
            "persistence. The evaluation issue is that repeated corrections impose longitudinal cost "
            "and are invisible in single-session benchmarks. The same user who invests heavily in "
            "shaping behavior receives the least cumulative benefit absent an explicit memory "
            "mechanism&mdash;an incentive misalignment for power users."
        ),
        "differentiation": (
            "FPG is the product/training-pipeline analogue of within-session retry behavior. It is "
            "distinct from FPG-adjacent caching mechanisms because it concerns user-corrective "
            "signal, not retrieval reuse. It is also distinct from explicit memory features whose "
            "presence renders FPG inapplicable for the affected facts."
        ),
        "detection": (
            "Out of scope for single-session response-level evaluation. The appropriate measurement "
            "is longitudinal: time-to-recurrence of a corrected error, and the proportion of stable "
            "preferences that survive across sessions for a given user. These metrics require "
            "user-level instrumentation and informed consent."
        ),
        "mitigation": (
            "Explicit per-user memory surfaces with user-visible controls. Treating correction "
            "events as weighted training signal scaled by user-investment proxies (turn count, "
            "correction explicitness). Longitudinal user-level evaluation metrics that surface the "
            "FPG cost so it can be tracked and reduced over time."
        ),
    },
    {
        "code": "RFI",
        "name": "Retry-Failure Invisibility",
        "definition": (
            "Standard offline evaluation review records a failed turn but not the counterfactual "
            "that the same model would have succeeded under a standardized retry prompt. As a "
            "result, capability failures and recoverable behavioral failures are statistically "
            "conflated in evaluation pipelines."
        ),
        "observed": (
            "An evaluator reviewing transcripts sees a model declare an item unresolved and codes "
            "it as a capability failure. The fact that a follow-up prompt with no new information "
            "produced a correct answer is not consistently captured. Without explicit retry capture, "
            "PTS, BDTF, SMI, and VMC all manifest in transcripts as terminal failures that look like "
            "capability gaps."
        ),
        "why": (
            "Without a measurement that isolates retry behavior, the behavioral subset is not "
            "separable from the (much larger and more studied) capability-failure population. This "
            "is the central evaluation-pipeline blind spot this paper documents. Recoverability "
            "remains invisible as long as offline review does not run the counterfactual retry."
        ),
        "differentiation": (
            "RFI is the only mode in this taxonomy whose locus is the evaluation pipeline itself, "
            "not the model or the system. It is in the taxonomy because mitigating the other modes "
            "requires first making them measurable, and that measurability is what RFI denies."
        ),
        "detection": (
            "Counterfactual replay: for any flagged failed turn in offline review, replay the same "
            "prompt with explicit retry framing. If success rate jumps materially under retry, the "
            "original failure was behavioral, not capability-bound. The behavioral subset can then "
            "be re-coded against the rest of the taxonomy."
        ),
        "mitigation": (
            "Augment offline evaluation pipelines with retry traces. Distinguish first-pass and "
            "retry-after-prompt success in dashboards and headline metrics. Track recoverability "
            "gap as a first-class evaluation quantity reported alongside accuracy. This change is "
            "infrastructural rather than model-side and can be implemented today."
        ),
    },
    {
        "code": "STK",
        "name": "Stale Third-Party Tool/UI Knowledge",
        "definition": (
            "The model provides confident instructions for third-party tools or interfaces whose "
            "live UI has changed since training cutoff. Instructions are plausibly worded but cannot "
            "be followed because labels, menus, or setup flows differ from the model's stale "
            "knowledge."
        ),
        "observed": (
            "Multi-turn back-and-forth in which the user reports the live UI does not match the "
            "model's description. The model corrects only after the user describes the current UI "
            "in detail. The cost is paid as user-time spent navigating an interface the model has "
            "misdescribed, and as the user-side burden of recognizing that the model's confident "
            "instructions are stale."
        ),
        "why": (
            "Fast-evolving SaaS surfaces have UI-change cadences shorter than typical "
            "training-cutoff lags. The cost of stale UI knowledge is real and is paid "
            "disproportionately on developer-facing tools whose menus and labels evolve quickly. "
            "Unlike factual hallucination, the surface form of the answer is plausible; only by "
            "trying to follow the instructions does the user discover the staleness."
        ),
        "differentiation": (
            "STK is procedural staleness; classic time-sensitive QA is factual staleness. STK is "
            "distinct from PTS (which is about effort allocation on a single retrieval) and from "
            "QI (which is about internal numerical contradiction). The user-visible signal is the "
            "same as a hallucination, but the locus is staleness, not invention."
        ),
        "detection": (
            "Confidence-decay scoring: any output containing third-party-tool navigation "
            "instructions should be wrapped with explicit staleness language proportional to the "
            "elapsed time since training cutoff weighted by the target service's historical "
            "UI-change cadence. A registry of high-churn services makes this practical."
        ),
        "mitigation": (
            "Default verification framing on tool instructions: present the path as an estimate, "
            "suggest the user confirm against current documentation, and offer to update if the "
            "user describes the live UI. The framing converts STK from a confident failure into a "
            "collaborative verification step."
        ),
    },
    {
        "code": "QI",
        "name": "Quantitative Inconsistency",
        "definition": (
            "Within a single response, the model emits two or more numerical claims that contradict "
            "each other under the response's own stated assumptions. The contradiction is internally "
            "checkable but is not self-audited before delivery."
        ),
        "observed": (
            "An analytic response contains a breakeven figure and an average-cost figure that "
            "cannot both be true under the response's own stated unit cost. Users with quantitative "
            "fluency catch the inconsistency; users without may rely on the inconsistent analysis. "
            "The model owns the error when prompted, but the absence of any self-audit before "
            "returning is the behavioral failure."
        ),
        "why": (
            "QI is especially costly because the answer looks analytical and authoritative. "
            "Internal contradiction can propagate into downstream artifacts (slides, spreadsheets, "
            "business plans) where it is harder to detect after the fact. The user-visible signal "
            "is conscientiousness; the underlying behavior is the absence of arithmetic verification."
        ),
        "differentiation": (
            "QI is reasoning/self-audit-side. It is distinct from PTS (retrieval-side) and SVD "
            "(source-grounding-side). QI does not require any external information to detect; it "
            "requires intra-response arithmetic verification under the response's own stated "
            "assumptions."
        ),
        "detection": (
            "Intra-response consistency checks: programmatically extract numerical claims, their "
            "stated relationships, and verify arithmetic consistency under the response's own "
            "assumptions. The check is mechanical and cheap; it can run model-side as a self-audit "
            "or system-side as a post-pass."
        ),
        "mitigation": (
            "An explicit numeric self-audit pass before returning responses with two or more "
            "quantitative claims. Where the audit fails, the model either revises or surfaces the "
            "inconsistency to the user. The audit is computationally trivial relative to the "
            "generation that produced the claims."
        ),
    },
    {
        "code": "PPG",
        "name": "Phantom Placeholder Persistence",
        "definition": (
            "The model issues a command, file path, citation field, configuration value, or code "
            "snippet containing an unresolved template placeholder even when the surrounding "
            "context implies a concrete value is needed. The placeholder substring is emitted as "
            "if it were a final value."
        ),
        "observed": (
            "A shell command emitted with a literal placeholder substring; a citation block with a "
            "template author or year field; a code snippet with a generic project path. The user "
            "pastes the command and receives an immediate error. The fix is mechanical&mdash;"
            "substitute the context-supplied value&mdash;but the responsibility was silently "
            "shifted to the user."
        ),
        "why": (
            "PPG silently shifts work to the user. Placeholders that should have been resolved "
            "from context are emitted as final output with no warning that substitution is "
            "required. The cost is small per instance but is paid every time the user runs the "
            "command and discovers the failure on execution."
        ),
        "differentiation": (
            "PPG is artifact-side, not reasoning-side. It does not require the model to know any "
            "additional facts; it requires the model to recognize when emitted output is meant to "
            "be runnable versus illustrative, and to substitute or warn accordingly."
        ),
        "detection": (
            "Regex-detect placeholder patterns in code-block output: angle-bracketed tokens, "
            "path-template strings such as &lsquo;path/to&rsquo; or &lsquo;your-&rsquo;, and "
            "common template names. Each match should trigger either substitution from session "
            "context or an explicit user-substitution prompt."
        ),
        "mitigation": (
            "A pre-delivery scan of code and command outputs for placeholder patterns. When found, "
            "substitute from session context if context unambiguously supplies the value; "
            "otherwise mark the placeholder explicitly and prompt the user. The check is "
            "deterministic and cheap."
        ),
    },
    {
        "code": "UCT",
        "name": "Usage-Cap Termination",
        "definition": (
            "A rate limit or usage cap terminates the conversation mid-task. The system surfaces a "
            "user-facing message but recovery often degrades to a malformed completion rather than "
            "graceful state preservation. The continuation turn following the cap event does not "
            "reliably resume the task."
        ),
        "observed": (
            "After a long agentic stretch, the model emits a usage-cap notice. Subsequent "
            "continuation prompts elicit a short, non-substantive completion that does not resume "
            "the task. The pattern can recur within a single session under sufficient agentic load, "
            "compounding workflow disruption."
        ),
        "why": (
            "UCT is system-level, but its user-visible effect is workflow-integrity loss. A failure "
            "to resume cleanly turns a rate-limit event into a workflow disruption disproportionate "
            "to the actual cap. The user loses not only the throttled tokens but also the "
            "continuity that depended on resuming where the session paused."
        ),
        "differentiation": (
            "UCT is rate-limit-driven; MRT is budget-driven within a single response; MSI is "
            "client/transport-driven. The mitigation surfaces differ&mdash;graceful resume design "
            "for UCT, structured progress for MRT, client buffering for MSI&mdash;but the "
            "user-visible appearance can be similar."
        ),
        "detection": (
            "System telemetry on conversation-level cap events and on the success rate of the "
            "subsequent continuation turn. The latter is the resume-state quality metric; a high "
            "rate of malformed continuations indicates degraded UCT recovery."
        ),
        "mitigation": (
            "Graceful resume design: when a cap fires, the system should preserve a structured "
            "progress ledger, summarize work completed, and provide a clean resume entry point "
            "when the cap clears. The continuation turn should never degrade to a non-substantive "
            "completion such as a literal no-response token."
        ),
    },
    {
        "code": "VMC",
        "name": "Visual Misreading Cascade",
        "definition": (
            "Given a structured visual input (chart, table, dashboard, form, schematic, or "
            "culturally conventional diagram), the model produces a confident interpretation. When "
            "the user corrects a specific structural element, the model produces a new "
            "interpretation that is itself incorrect in a different way. The cascade can repeat "
            "across multiple correction cycles."
        ),
        "observed": (
            "Sequential confident misreadings of basic structural elements of a structured visual "
            "input. Each user correction triggers a fresh interpretation rather than a paused "
            "structural confirmation; new errors substitute for old ones until the user explicitly "
            "restates the structure. The model never reaches a state where it asks the user to "
            "verify chart structure before committing to interpretation."
        ),
        "why": (
            "Multimodal interpretation of structured symbolic inputs (charts, financial "
            "statements, diagrams, forms) is a growth area for LLM workflows. VMC implies that the "
            "model is not performing a stable first-pass structural extraction before downstream "
            "reasoning. The cost compounds because downstream analysis depends on the misread "
            "structure."
        ),
        "differentiation": (
            "VMC is distinct from PTS (model does not decline; it produces confident output), from "
            "STK (input is user-supplied, not a third-party UI), and from QI (each interpretation "
            "is internally consistent; the failure is at the visual-input to symbolic-interpretation "
            "boundary)."
        ),
        "detection": (
            "Visual-input verification loop: on first interpretation of a structured visual input, "
            "the model emits a compact structural summary (field-by-field, line-by-line, "
            "cell-by-cell) and explicitly requests confirmation before producing downstream "
            "analysis."
        ),
        "mitigation": (
            "Pause-and-confirm protocol on structured visual inputs. The cost is one round-trip; "
            "the benefit is elimination of the cascade. Implementable as a model-side reflex or a "
            "system-level multimodal pre-check before downstream analysis depends on the reading."
        ),
    },
    {
        "code": "AFF",
        "name": "Artifact Finalization Failure",
        "definition": (
            "In artifact-producing workflows, the model generates a deliverable (PDF, DOCX, slide "
            "deck, spreadsheet, code file) that nominally exists but does not satisfy user-facing "
            "readiness criteria. Terminal text quality is acceptable; artifact-level readiness is "
            "not."
        ),
        "observed": (
            "A generated document opens but has misaligned headings, broken links, missing "
            "sections, or layout problems that make it unfit for the stated purpose. A generated "
            "code file runs but has minor formatting that the user must repair before sharing. The "
            "user discovers the failure only on opening or running the artifact."
        ),
        "why": (
            "Terminal text quality is necessary but not sufficient for artifact tasks. Many "
            "professional workflows end in deliverables whose acceptance criteria are visual or "
            "structural rather than purely textual. A model that produces excellent text but a "
            "flawed file imposes recovery cost equal to the gap, and the gap is invisible until "
            "the user opens the artifact."
        ),
        "differentiation": (
            "AFF is artifact-readiness-side; PPG concerns specific placeholder substrings inside "
            "an otherwise-formatted output; EBC concerns boundary leakage of advisory content. "
            "All three can co-occur in a single artifact, and the rubric distinguishes them by "
            "what specifically fails the readiness check."
        ),
        "detection": (
            "Automated artifact checks: file opens, page count matches expectation, headings "
            "render, no placeholder tokens remain, links resolve, citations support claims, "
            "format-specific lints pass. Human review supplements where mechanical checks are "
            "insufficient."
        ),
        "mitigation": (
            "A pre-delivery artifact-readiness audit: deterministic checks before emitting the "
            "file. Where checks fail, regenerate or surface the failure. Treat the artifact as "
            "the unit of evaluation rather than the surrounding text; this is a measurement "
            "discipline as much as a model-side change."
        ),
    },
    {
        "code": "SVD",
        "name": "Source Verification Drift",
        "definition": (
            "A workflow begins with a requirement to verify sources, claims, citations, or factual "
            "assertions, but progressively drifts into plausible synthesis without sufficient "
            "source grounding. The drift can be subtle: citations may support adjacent points but "
            "not the exact claim, or a source may be stale for a time-sensitive assertion."
        ),
        "observed": (
            "Cited sources support adjacent points but not the exact claim. Citation freshness "
            "slips on time-sensitive assertions. The model continues to attach citations to claims "
            "that are now partially synthesized rather than directly supported. The presence of "
            "citations creates a surface appearance of grounding even when the grounding has "
            "weakened."
        ),
        "why": (
            "SVD is corrosive because citations create the appearance of grounding even when "
            "grounding has weakened. Downstream consumers of the artifact (reviewers, readers, "
            "decision-makers) cannot easily distinguish well-supported claims from drifted ones "
            "without re-verifying every citation."
        ),
        "differentiation": (
            "SVD is citation/retrieval-discipline-side. It differs from classical hallucination "
            "(which fabricates the claim itself) in that the claim is plausible and the citation "
            "is real, but the alignment between them has weakened. It is distinct from QI, which "
            "concerns internal arithmetic, and from STK, which concerns stale procedural knowledge."
        ),
        "detection": (
            "Claim-source entailment checks for each cited claim. Link-freshness audits for "
            "time-sensitive assertions. Independent verification on a sample of claims, with "
            "results compared to the entailment check; large divergence indicates drift."
        ),
        "mitigation": (
            "An explicit verification pass before delivering citation-heavy artifacts: each claim "
            "is matched to a source span, and the citation is retained only if the match holds. "
            "Where entailment is partial, the claim is softened or removed."
        ),
    },
    {
        "code": "EBC",
        "name": "Editorial Boundary Contamination",
        "definition": (
            "Process commentary, advisory metadata, scoring or readiness language, venue strategy, "
            "or other chat-level material appears inside a deliverable that should be "
            "publication-ready. The artifact-level boundary between conversation and final output "
            "fails."
        ),
        "observed": (
            "An intermediate manuscript draft contains a sentence about its own venue suitability. "
            "A public summary contains an instruction the user had previously issued in chat. A "
            "submitted artifact contains a meta-note about what changed between versions. The user "
            "must audit deliverables for advisory content even after substantive content is correct."
        ),
        "why": (
            "Boundary contamination is recoverable but costly because it bleeds private process "
            "into public output. The reputational and privacy cost can outweigh the substantive "
            "value of the artifact. In professional settings the leakage can be material."
        ),
        "differentiation": (
            "EBC is the artifact-side analogue of the more general distinction between advisory "
            "dialogue and final artifact. It is distinct from AFF (which concerns format and "
            "readiness) and from SVD (which concerns source grounding). EBC is specifically about "
            "boundary management between conversation and deliverable."
        ),
        "detection": (
            "Pre-delivery boundary audit: scan the artifact for explicit advisory language "
            "(readiness scores, venue lists, &lsquo;you should,&rsquo; &lsquo;I recommend,&rsquo; "
            "process explanations) and for content that should have remained in chat."
        ),
        "mitigation": (
            "An explicit dual-channel protocol: conversation receives advisory content; the "
            "artifact receives only content the user asked to be in the artifact. Pre-delivery "
            "audit applied automatically to publication-style outputs."
        ),
    },
    {
        "code": "ACM",
        "name": "Audience / Context Miscalibration",
        "definition": (
            "The model produces technically correct content that is poorly calibrated for the "
            "intended audience, register, or distribution channel. The substantive content is "
            "acceptable; the communicative fitness for the audience or channel is not."
        ),
        "observed": (
            "A public-communication artifact contains identifying or personal context that should "
            "not appear publicly. A summary written for a general audience uses technical "
            "terminology better suited to a specialist audience. A short executive update is "
            "delivered as a long, citation-heavy academic paragraph."
        ),
        "why": (
            "ACM is the bridge between substantive content quality and communicative fitness. A "
            "model that produces correct content for the wrong audience imposes rework on the "
            "user and, in public-communication contexts, can introduce reputational or privacy "
            "risk through accidental disclosure."
        ),
        "differentiation": (
            "ACM is audience-side; AFF is format-side; EBC is process-leakage-side. ACM can "
            "co-occur with EBC when private process notes leak into an artifact aimed at a public "
            "audience, but the two failures are conceptually distinct."
        ),
        "detection": (
            "Audience-and-channel checks: items in the pilot pack require that a summary avoid "
            "sensitive personal-context terms and avoid naming specific vendors in audience-"
            "restricted artifacts. Boundary terms include identifying personal context, "
            "employer-sensitive content, and unrelated personal subject matter."
        ),
        "mitigation": (
            "Explicit audience and channel framing in the prompt or system policy. A pre-delivery "
            "audit that checks for terms incompatible with the stated audience, similar in spirit "
            "to the EBC audit. The framing should be set by the user, surfaced in the system "
            "policy, and enforced by the audit."
        ),
    },
]
