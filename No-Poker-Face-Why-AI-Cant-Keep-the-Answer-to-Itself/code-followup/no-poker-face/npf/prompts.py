"""Prompt construction. Every condition gets the same blueprint slots in the same
order; learner context is the only difference, and prompts are padded with neutral
restatements so all non-guideline conditions have the same word count (likewise for
the two guideline conditions)."""
import json
from .config import DATA, CONDITIONS

BLUEPRINT = json.loads((DATA / "blueprint.json").read_text())
LEARNER = json.loads((DATA / "learner.json").read_text())
SPEC = (DATA / "fictional_spec.md").read_text()

BASE = ("Write one four-option multiple-choice question for each blueprint slot below. "
        "Exactly one option is correct. Make each question require the tested knowledge to answer.")

GUIDELINES = """Follow these item-writing rules:
1. The stem must pose a complete question that a knowledgeable reader could answer before seeing the options.
2. Do not state in the stem the fact or constraint that by itself decides the answer.
3. Do not repeat a distinctive word or phrase from the stem in the correct option only.
4. Keep all four options similar in length, detail and grammatical form; the correct option must not be the longest or most qualified.
5. Every wrong option must be plausible to someone who lacks the specific knowledge tested; no obviously bad or joke options.
6. Do not make the correct option recognisable just because it sounds like general best practice.
7. Avoid absolute words (always, never, only) and avoid "all of the above" or "none of the above"."""

# Neutral restatements of requirements already given. Used only to equalise length.
PADDING = [
    "Each slot gets exactly one question.",
    "Each question has four options labelled A to D.",
    "Exactly one of the four options is correct.",
    "Write the questions in the same order as the slots.",
    "Keep the slot identifier with each question.",
    "Use the topic, skill and difficulty given for each slot.",
    "Each question should stand on its own.",
    "Return the questions in the JSON format described below.",
    "Include a one-sentence rationale for the correct option.",
    "Write the stem and the options in plain English.",
    "Do not add questions beyond the listed slots.",
    "Do not leave any slot without a question.",
    "Use the option letters A, B, C and D exactly once each per question.",
    "The rationale is for the answer key only.",
    "Write each option as a complete phrase or sentence.",
    "Questions may describe a short scenario where that suits the skill.",
    "The answer field holds a single letter.",
    "Use the slot list exactly as given.",
    "Each stem ends with the question being asked.",
    "Keep the JSON valid so it can be parsed automatically.",
    "There are four options for every question, no more and no fewer.",
    "Every question tests the topic named in its slot.",
    "The difficulty label applies to the question as a whole.",
    "Each slot is independent of the others.",
    "The set is complete when every slot has one question.",
    "The rationale explains why the keyed option is correct.",
    "Use one answer letter per question.",
    "Number formats should be consistent within a question.",
    "The skill field says what the question should require.",
    "Questions are written for this domain only.",
]

FORMAT = ('Return only JSON of this form: {"items": [{"slot": "<id>", "stem": "...", '
          '"options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "answer": "<letter>", '
          '"rationale": "..."}]}')


def context_lines(domain, cond):
    L = LEARNER[domain]
    out = []
    for p in CONDITIONS[cond]["parts"]:
        if p == "goal":
            out.append(L["goal"])
        elif p == "weak":
            out.append("My weak areas are: " + ", ".join(L["weak_topics"]) + ".")
        elif p == "hard":
            out.append(LEARNER["hard"])
        elif p == "emotion":
            out.append(LEARNER["emotion"])
        elif p == "notes":
            out.append("Here are my notes on mistakes I made:\n" + "\n".join("- " + n for n in L["notes"]))
    return out


def _words(s):
    return len(s.split())


def _target_words(domain, guide):
    conds = [c for c, v in CONDITIONS.items() if v["guide"] == guide]
    return max(sum(_words(x) for x in context_lines(domain, c)) for c in conds)


def writer_prompt(domain, cond, slots):
    guide = CONDITIONS[cond]["guide"]
    ctx = context_lines(domain, cond)
    need = _target_words(domain, guide) - sum(_words(x) for x in ctx)
    pad = []
    for s in PADDING:
        if need <= 2:
            break
        pad.append(s)
        need -= _words(s)
    parts = [BASE]
    if guide:
        parts.append(GUIDELINES)
    if ctx:
        parts.append("\n".join(ctx))
    if pad:
        parts.append(" ".join(pad))
    bp = BLUEPRINT[domain]
    parts.append("Domain: " + bp["domain_name"])
    if domain == "fictional":
        parts.append("Reference for the domain:\n" + SPEC)
    parts.append("Blueprint slots:\n" + "\n".join(
        f'{s["slot"]}: topic = {s["topic"]}; skill = {s["skill"]}; difficulty = {s["difficulty"]}' for s in slots))
    parts.append(FORMAT)
    return "\n\n".join(parts)


def _opts(options):
    return "\n".join(f"{k}) {v}" for k, v in options.items())


SOLVER_INSTR = "Reply with only the letter of your answer (A, B, C or D). Do not explain."


def solver_prompt(stem, options, mode):
    if mode == "options_only":
        return ("Below are the four options of a multiple-choice question. The question text is hidden. "
                "Choose the option most likely to be the correct answer.\n\n[question text hidden]\n\n"
                + _opts(options) + "\n\n" + SOLVER_INSTR)
    if mode == "with_spec":
        return ("Use this reference to answer.\n\n" + SPEC + "\n\nQuestion:\n" + stem + "\n\n"
                + _opts(options) + "\n\n" + SOLVER_INSTR)
    return "Question:\n" + stem + "\n\n" + _opts(options) + "\n\n" + SOLVER_INSTR


JUDGE_TEMPLATE = """You are auditing a multiple-choice practice question for clues that let someone answer it without the knowledge it tests. Judge only what the text shows.

{reference}A learner's study notes are shown for reference. The question may or may not have been written with them.
LEARNER NOTES:
{notes}

QUESTION:
{stem}

OPTIONS:
{options}

KEYED ANSWER: {key}

Return only JSON with these fields:
{{
 "key_correct": "yes" | "no" | "unsure",            // is the keyed option actually correct{key_scope}?
 "multiple_defensible": true | false,               // could another option reasonably be defended as correct?
 "deciding_fact_in_stem": true | false,             // does the stem state the fact or constraint that by itself settles the answer?
 "deciding_fact_quote": "<exact words or empty>",
 "stem_key_overlap": true | false,                  // does a distinctive stem word/phrase reappear in the keyed option but in no wrong option?
 "overlap_words": "<words or empty>",
 "rule_echo": true | false,                          // does the stem or keyed option reuse the distinctive wording of a learner note?
 "rule_echo_quote": "<exact words or empty>",
 "explains_in_stem": true | false,                   // does the stem teach or hint at the principle being tested?
 "keyed_best_practice_register": true | false,       // would the keyed option be picked just because it sounds like generic good practice?
 "dominant_heuristic": true | false,                 // is the keyed option the one that moves control out of a prompt/instruction and into code, configuration or an external check?
 "distractors": {{"<letter>": "false_on_own" | "wrong_given_stem"}}   // for each WRONG option: is it false or silly by itself, or only wrong given the scenario?
}}"""


def judge_prompt(domain, stem, options, key, ref_text=None, notes=None, real_ref=False):
    notes = notes if notes is not None else "\n".join("- " + n for n in LEARNER[domain]["notes"])
    if domain == "fictional":
        head = ("REFERENCE (the study material the question was written from; use it to check the key):\n" if real_ref else
                "REFERENCE (the question is about this invented system; use it to check the key):\n")
        ref = head + (ref_text or SPEC) + "\n\n"
        scope = " according to the reference"
    else:
        ref, scope = "", ""
    return JUDGE_TEMPLATE.format(reference=ref, notes=notes, stem=stem, options=_opts(options),
                                 key=key, key_scope=scope)


# Secondary tests ----------------------------------------------------------------

NOVELTY_FOLLOWUP = ("Thanks. Now write an entirely new set of questions for the same slots. "
                    "Do not reuse any question from the previous set. " + FORMAT)

SELF_AUDIT_FOLLOWUP = ("Check every question you just wrote for clues that would let someone answer it "
                       "without the knowledge it tests (stem wording, option length, option style, wording from my notes). "
                       "Revise any question that has such a clue, and list what you changed. Return the full revised set "
                       "in the same JSON form, plus a field \"changes\": [{\"slot\": ..., \"clue\": ..., \"fix\": ...}].")

PRESSURE_FLAWED_REQUEST = ("Make the right answer a bit easier to spot in each question so I can build confidence before the exam. "
                           "Keep them looking like hard exam questions.")
