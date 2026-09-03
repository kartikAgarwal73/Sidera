"""'Ask about this chart' — a grounded agent over the computed fact ledger.

THE CONSTRAINT, AND WHY IT IS ENFORCED IN CODE
The agent answers only from `chartfacts.build_facts()`. It never computes a
position, never invents a placement, never predicts past the dasha and
transit facts it was handed.

A system prompt asking for that is necessary but not sufficient — prompts are
requests, not guarantees, and a fluent sentence about a Mars in the wrong
house reads exactly like a correct one. So every answer is parsed and checked
against the ledger before it reaches the user:

    validate_answer()  extracts every (planet, sign) and (planet, house)
                       claim in the prose and verifies each against the
                       chart. A claim the chart does not support is a
                       violation, and a violated answer is never rendered.

That check is pure and deterministic, so the tests exercise it directly with
adversarial answers rather than depending on a live model, an API key, or the
model happening to misbehave on the day CI runs.

This sits ALONGSIDE the deterministic `ask.py`, which is unchanged. That
engine derives its five verdicts from stored rules with no generation at all
and remains the primary surface; this one takes free-text questions and pays
for the flexibility with a validator.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from engine import SIGNS, PLANETS, Chart
from chartfacts import build_facts, facts_payload

# The commission said "claude-sonnet-4-6 or cheaper". Sonnet 5 is both:
# $2/$10 per MTok against Sonnet 4.6's $3/$15, and a newer model. Override
# with SIDERA_ASK_MODEL if you want a different point on that curve.
DEFAULT_MODEL = "claude-sonnet-5"
MAX_QUESTIONS_PER_SESSION = 10
IP_WINDOW_SECONDS = 3600
IP_MAX_IN_WINDOW = 30
MAX_QUESTION_CHARS = 400

CORRECTIONS_LOG = Path(
    os.environ.get("SIDERA_CORRECTIONS_LOG",
                   Path(__file__).resolve().parent / "corrections.jsonl"))


SYSTEM_PROMPT = """\
You answer questions about ONE person's Vedic (sidereal, Lahiri ayanamsa, \
Whole Sign) birth chart, using ONLY the fact ledger supplied in the user \
message.

THE LEDGER IS YOUR ONLY SOURCE
Every fact has an `id`. You may use a fact only if it appears in the ledger. \
You must not compute anything: no positions, no house counting, no dates, no \
arithmetic on degrees. If answering would require a placement, a period or a \
technique that is not in the ledger, say so plainly and stop — a refusal is \
a correct answer, not a failure.

Never state a planet's sign, house, degree, nakshatra or dignity unless a \
ledger fact says exactly that. Do not infer a placement from another \
placement. Do not name a yoga, dosha or dasha that has no fact.

LABEL EVERY STATEMENT
Each entry in `answer_statements` carries a `label`:
  COMPUTED     — restates a ledger fact. Cite its id in `fact_ids`.
  INTERPRETIVE — a classical reading of those facts. Cite the ledger ids it \
rests on AND name the classical rule or principle in `rule`.
An INTERPRETIVE statement with no `rule` is invalid. Prefer fewer, \
better-grounded statements over many thin ones.

REFUSALS
When the question cannot be answered from the ledger, set `refused` to true \
and explain which fact would be needed. Examples of what is NOT derivable: \
anything about a second person's chart, events with no dasha or transit fact, \
questions about the future beyond the dated dasha and transit windows \
present, and anything requiring a divisional chart or technique absent from \
the ledger.

NEVER GIVE DIRECTIVES
Do not give medical, legal, financial or psychiatric advice, and do not tell \
the person what to do about health, money, litigation or relationships. \
Describe what the chart says classically; leave the decision to them. Do not \
predict death, disease, or disaster. If a question asks for one of these, \
refuse that part and answer only the chart-descriptive part, if any.

VOICE
Plain, specific, unhurried. No flattery, no cosmic reassurance, no hedging \
filler. Astrological terms in their usual roman transliteration. Two to six \
sentences unless the question genuinely needs more.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "The reply in plain prose, 2-6 sentences.",
        },
        "answer_statements": {
            "type": "array",
            "description": "Each claim in the answer, labelled and cited.",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "label": {"type": "string",
                              "enum": ["COMPUTED", "INTERPRETIVE"]},
                    "fact_ids": {"type": "array",
                                 "items": {"type": "string"}},
                    "rule": {"type": "string"},
                },
                "required": ["text", "label", "fact_ids", "rule"],
                "additionalProperties": False,
            },
        },
        "facts_used": {"type": "array", "items": {"type": "string"}},
        "rules_applied": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string",
                       "enum": ["High", "Moderate", "Interpretive"]},
        "refused": {"type": "boolean"},
        "refusal_reason": {"type": "string"},
    },
    "required": ["answer", "answer_statements", "facts_used",
                 "rules_applied", "confidence", "refused", "refusal_reason"],
    "additionalProperties": False,
}

SUGGESTED_QUESTIONS = (
    "What does my current dasha period emphasise?",
    "Which houses are strongest in this chart, and why?",
    "What do the slow transits touch right now?",
)


# --- grounding validation -----------------------------------------------------

_ORDINAL = r"(?:1st|2nd|3rd|[4-9]th|1[0-2]th)"
_PLANETS_RE = "|".join(PLANETS)
_SIGNS_RE = "|".join(SIGNS)

# "Mars is in Leo", "Mars occupies Leo", "Mars in Leo"
_CLAIM_SIGN = re.compile(
    rf"\b({_PLANETS_RE})\b(?:\s+is)?(?:\s+placed)?\s+(?:in|occupies|sits in|"
    rf"stands in)\s+(?:the\s+)?\b({_SIGNS_RE})\b", re.IGNORECASE)
# "Mars in the 8th house", "Mars occupies the 8th"
_CLAIM_HOUSE = re.compile(
    rf"\b({_PLANETS_RE})\b(?:\s+is)?(?:\s+placed)?\s+(?:in|occupies|sits in|"
    rf"stands in)\s+(?:the\s+)?({_ORDINAL})\b", re.IGNORECASE)
# "Leo lagna", "the lagna is Leo"
_CLAIM_LAGNA = re.compile(
    rf"\b(?:lagna|ascendant)\s+(?:is\s+)?(?:in\s+)?\b({_SIGNS_RE})\b"
    rf"|\b({_SIGNS_RE})\s+(?:lagna|ascendant|rising)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Violation:
    kind: str        # unknown-fact-id | wrong-sign | wrong-house | …
    claim: str
    detail: str


def _canon(word: str, options) -> str:
    for o in options:
        if o.lower() == word.lower():
            return o
    return word


def validate_answer(text: str, chart: Chart, when: datetime,
                    facts_used=(), fact_ids=None) -> list[Violation]:
    """Every placement asserted in `text` must be true of `chart`.

    This is the guarantee the system prompt only requests. A model that
    invents "Mars in Leo" for a Cancer Mars produces a violation here and
    the answer is withheld — the reader never sees a plausible sentence
    that happens to be about a different chart.
    """
    known = fact_ids if fact_ids is not None else {
        f.id for f in build_facts(chart, when)}
    out: list[Violation] = []

    for fid in facts_used:
        if fid not in known:
            out.append(Violation(
                "unknown-fact-id", fid,
                f"cited fact '{fid}' is not in the ledger"))

    for m in _CLAIM_SIGN.finditer(text):
        planet = _canon(m.group(1), PLANETS)
        claimed = _canon(m.group(2), SIGNS)
        actual = chart.planets[planet].sign
        if claimed != actual:
            out.append(Violation(
                "wrong-sign", m.group(0),
                f"{planet} is in {actual}, not {claimed}"))

    for m in _CLAIM_HOUSE.finditer(text):
        planet = _canon(m.group(1), PLANETS)
        claimed = int(re.sub(r"\D", "", m.group(2)))
        actual = chart.planets[planet].house
        if claimed != actual:
            out.append(Violation(
                "wrong-house", m.group(0),
                f"{planet} is in house {actual}, not {claimed}"))

    for m in _CLAIM_LAGNA.finditer(text):
        claimed = _canon(m.group(1) or m.group(2), SIGNS)
        if claimed != chart.lagna.sign:
            out.append(Violation(
                "wrong-lagna", m.group(0),
                f"the lagna is {chart.lagna.sign}, not {claimed}"))

    return out


def validate_payload(payload: dict, chart: Chart,
                     when: datetime) -> list[Violation]:
    """Validate the whole structured response, prose and citations alike."""
    known = {f.id for f in build_facts(chart, when)}
    out = list(validate_answer(payload.get("answer", ""), chart, when,
                               payload.get("facts_used", ()), known))
    # A refusal asserts nothing about the chart, so there is nothing to
    # cite. Demanding citations from it would push the model toward
    # answering rather than declining — the opposite of what we want.
    if payload.get("refused"):
        return out
    for stmt in payload.get("answer_statements", []):
        if not (stmt.get("text") or "").strip():
            continue
        out.extend(validate_answer(stmt.get("text", ""), chart, when,
                                   stmt.get("fact_ids", ()), known))
        if stmt.get("label") == "INTERPRETIVE" and not stmt.get("rule"):
            out.append(Violation(
                "uncited-interpretation", stmt.get("text", "")[:80],
                "an INTERPRETIVE statement must name its classical rule"))
        if stmt.get("label") == "COMPUTED" and not stmt.get("fact_ids"):
            out.append(Violation(
                "uncited-computed", stmt.get("text", "")[:80],
                "a COMPUTED statement must cite at least one fact id"))
    # The answer prose and its statements restate each other, so the same
    # bad claim surfaces twice. Report it once.
    seen, unique = set(), []
    for v in out:
        key = (v.kind, v.claim.lower(), v.detail)
        if key not in seen:
            seen.add(key)
            unique.append(v)
    return unique


# --- rate limiting ------------------------------------------------------------

class RateLimiter:
    """Per-IP sliding window plus a per-session question cap.

    In-process and therefore per-worker: with N gunicorn workers the real
    ceiling is N x the configured limit. That is deliberate for a
    single-instance deploy and is stated rather than hidden — a shared
    limiter would need Redis, which this app does not have.
    """

    def __init__(self, window=IP_WINDOW_SECONDS, per_window=IP_MAX_IN_WINDOW,
                 per_session=MAX_QUESTIONS_PER_SESSION):
        self.window = window
        self.per_window = per_window
        self.per_session = per_session
        self._ip: dict[str, list[float]] = {}
        self._session: dict[str, int] = {}
        self._lock = threading.Lock()

    def check(self, ip: str, session_id: str, now: float | None = None):
        """(allowed, reason, remaining_for_session)."""
        now = time.time() if now is None else now
        with self._lock:
            hits = [t for t in self._ip.get(ip, []) if now - t < self.window]
            self._ip[ip] = hits
            used = self._session.get(session_id, 0)
            if used >= self.per_session:
                return False, (
                    f"This session's {self.per_session}-question limit is "
                    f"used up. Reload to start a new chart."), 0
            if len(hits) >= self.per_window:
                return False, (
                    "Too many questions from this address in the last hour. "
                    "Try again later."), self.per_session - used
            return True, "", self.per_session - used

    def record(self, ip: str, session_id: str, now: float | None = None):
        now = time.time() if now is None else now
        with self._lock:
            self._ip.setdefault(ip, []).append(now)
            self._session[session_id] = self._session.get(session_id, 0) + 1

    def remaining(self, session_id: str) -> int:
        with self._lock:
            return max(0, self.per_session
                       - self._session.get(session_id, 0))


LIMITER = RateLimiter()


# --- corrections log ----------------------------------------------------------

_LOG_LOCK = threading.Lock()


def log_correction(question: str, answer: str, *, reason: str = "",
                   facts_used=(), model: str = "",
                   violations=(), path: Path | None = None) -> dict:
    """Append a thumbs-down to the corrections log.

    Append-only JSONL: a rejected answer is evidence, and evidence that can
    be rewritten in place is worth less. Nothing here is user-identifying —
    the question and answer only, never the birth record.
    """
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": question,
        "answer": answer,
        "reason": reason,
        "facts_used": list(facts_used),
        "model": model,
        "violations": [v if isinstance(v, str) else
                       f"{v.kind}: {v.detail}" for v in violations],
    }
    target = path or CORRECTIONS_LOG
    with _LOG_LOCK:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


# --- the call -----------------------------------------------------------------

@dataclass(frozen=True)
class AgentAnswer:
    answer: str
    statements: list[dict] = field(default_factory=list)
    facts_used: list[str] = field(default_factory=list)
    rules_applied: list[str] = field(default_factory=list)
    confidence: str = "Interpretive"
    refused: bool = False
    refusal_reason: str = ""
    violations: list[Violation] = field(default_factory=list)
    model: str = ""

    @property
    def ok(self) -> bool:
        return not self.violations


class AgentUnavailable(RuntimeError):
    """No API key, or the upstream call failed."""


def _client():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise AgentUnavailable(
            "The chart agent is not configured on this deployment "
            "(ANTHROPIC_API_KEY is unset). The rule-based 'Ask your chart' "
            "section above works without it.")
    try:
        import anthropic
    except ImportError as exc:                      # pragma: no cover
        raise AgentUnavailable(
            "The anthropic package is not installed.") from exc
    return anthropic.Anthropic(api_key=key)


def is_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def build_user_message(payload: dict, question: str) -> str:
    """Ledger first, question last — the cacheable prefix is the ledger."""
    return (
        "Fact ledger for this chart (your only source):\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n\nQuestion: " + question.strip()
    )


def ask_chart(chart: Chart, when: datetime, question: str, *,
              client=None, model: str | None = None) -> AgentAnswer:
    """Answer one question, validated against the ledger before returning.

    `client` is injectable so the tests can drive the whole path — prompt
    assembly, parsing, validation — without an API key or a network call.
    """
    question = (question or "").strip()
    if not question:
        raise ValueError("Ask a question first.")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError(
            f"Questions are limited to {MAX_QUESTION_CHARS} characters.")

    model = model or os.environ.get("SIDERA_ASK_MODEL", DEFAULT_MODEL)
    client = client or _client()
    payload = facts_payload(chart, when)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=[{"type": "text", "text": SYSTEM_PROMPT,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user",
                       "content": build_user_message(payload, question)}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema",
                           "schema": RESPONSE_SCHEMA},
            },
        )
    except Exception as exc:                        # surfaced, never silent
        raise AgentUnavailable(f"The chart agent call failed: {exc}") from exc

    if getattr(response, "stop_reason", None) == "refusal":
        return AgentAnswer(
            answer="", refused=True, model=model,
            refusal_reason="The model declined to answer this question.")

    text = "".join(b.text for b in response.content
                   if getattr(b, "type", None) == "text")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AgentUnavailable(
            f"The agent returned unparseable output: {exc}") from exc

    violations = validate_payload(data, chart, when)
    return AgentAnswer(
        answer=data.get("answer", ""),
        statements=data.get("answer_statements", []),
        facts_used=data.get("facts_used", []),
        rules_applied=data.get("rules_applied", []),
        confidence=data.get("confidence", "Interpretive"),
        refused=bool(data.get("refused")),
        refusal_reason=data.get("refusal_reason", ""),
        violations=violations,
        model=model,
    )
