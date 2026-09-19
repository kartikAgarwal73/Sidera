"""The resolver — fires the predicates on one chart's ledger for one rule
set, groups what fired by FRAME, and returns one serialisable
ResolverOutput that carries a FrameResult for every frame the rule set
declares.

WHAT IT PROMISES
  * One FrameResult per declared frame, always. A frame with no result is
    a ResolverError, never an empty slot (the owner's C4-b).
  * A finding belongs to ONE frame — its predicate's declared frame — so a
    rule that reads two frames cannot vote twice.
  * A frame's status is `value` when something in it weighed or dated, and
    `silent` when it was read and nothing did: the findings are there,
    cited at weight 0, or there are none. A fact a predicate could not find
    is neither: it is carried in `missing`, and the validator withholds on
    it, because "nothing to add" would claim the frame was read.
  * The frame verdict is the C3-c rows in conditions.FRAME_VERDICT, and
    `disagreement` is always present. The balance the owner signed
    (conditions.balance) is carried beside it and never replaced by it.
  * Timing rule sets carry in_play / quiet / silent per frame, never a
    polarity; two dated frames that differ are a split.
  * Deterministic: the same ledger, rule set and moment give the same
    output, findings sorted, and as_dict() is plain JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
from datetime import datetime

import conditions
import schools
from conditions import (BALANCE_KINDS, MISSING, TIMING_KINDS, Finding,
                        frame_polarity, frame_verdict, timing_status)
from frames import ANCHOR, FRAMES
from rulesets import RULESETS, RuleSet


class ResolverError(RuntimeError):
    """A declared frame with no FrameResult, an undeclared frame with
    findings, or an anchor the ledger lacks. A programming error, raised —
    never a reading with a hole in it."""


@dataclass(frozen=True)
class FrameResult:
    frame: str
    status: str                       # value | silent
    polarity: str | None              # favourable | unfavourable | mixed | None
    timing: str | None                # in_play | quiet | silent | None
    support: int
    strain: int
    findings: tuple[str, ...]         # "rule_id/slot" of each finding here
    fact_ids: tuple[str, ...]         # everything read here, anchor included
    anchor: str
    missing: tuple[str, ...] = ()     # fact ids a predicate here could not find
    reason: str = ""                  # silent only: cited_only | no_finding

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ResolverOutput:
    ruleset: str
    base: str
    timing: bool
    when: str                         # ISO date
    findings: tuple[Finding, ...]
    frames: tuple[FrameResult, ...]   # in frames.FRAMES order, one per declared frame
    verdict: str                      # favourable | unfavourable | split | undecided | in_play | quiet | silent
    disagreement: tuple[str, ...]     # always present; () when the frames agree
    spoke: tuple[str, ...]            # the frames that voted
    balance: tuple[str, str]          # conditions.balance — the signed weights
    missing: tuple[str, ...]          # every fact id any predicate could not find
    schools: dict                     # the selection the ledger was read under

    def frame(self, name: str) -> FrameResult:
        for fr in self.frames:
            if fr.frame == name:
                return fr
        raise KeyError(name)

    def as_dict(self) -> dict:
        return {
            "ruleset": self.ruleset, "base": self.base, "timing": self.timing,
            "when": self.when,
            "findings": [f.as_dict() for f in self.findings],
            "frames": [fr.as_dict() for fr in self.frames],
            "verdict": self.verdict, "disagreement": list(self.disagreement),
            "spoke": list(self.spoke), "balance": list(self.balance),
            "missing": list(self.missing), "schools": dict(self.schools),
        }


_STEP_ORDER = {s: i for i, s in enumerate(conditions.STEPS)}


def predicates_for(rs: RuleSet) -> list[conditions.Predicate]:
    return [p for p in conditions.applicable(rs.domain) if p.step in rs.steps]


def check_ruleset(rs: RuleSet) -> list[str]:
    """The two declaration invariants, as findings a gate can print: every
    declared frame is some applicable predicate's frame, and every
    applicable predicate's frame is declared (a cite-only predicate has
    none and is exempt)."""
    problems = []
    frames_of = {p.frame_for(rs.varga) for p in predicates_for(rs)}
    frames_of.discard(None)
    for f in rs.frames:
        if f not in frames_of:
            problems.append(f"{rs.id}: declared frame {f} has no predicate")
    for f in sorted(frames_of):
        if f not in rs.frames:
            problems.append(f"{rs.id}: predicate frame {f} is not declared")
    return problems


def resolve(ruleset: str | RuleSet, facts: dict, when: datetime) -> ResolverOutput:
    rs = RULESETS[ruleset] if isinstance(ruleset, str) else ruleset
    problems = check_ruleset(rs)
    if problems:
        raise ResolverError("; ".join(problems))
    preds = predicates_for(rs)

    # Fire, and attribute each finding to the frame of the predicate that
    # fired it — the evaluator says which, so nothing is inferred.
    findings: list[Finding] = []
    for p, f in conditions.evaluate_by_predicate(rs.domain, facts, when,
                                                 only=preds):
        frame = p.frame_for(rs.varga)
        if frame is not None and frame not in rs.frames:
            raise ResolverError(
                f"{rs.id}: finding {f.rule_id}/{f.slot} is attributed to "
                f"{frame}, which the rule set does not declare")
        findings.append(replace(f, frame=frame or ""))
    findings.sort(key=lambda f: (_STEP_ORDER[f.step], f.rule_id, f.slot,
                                 f.fact_ids, f.start or "", f.end or ""))

    # One FrameResult per declared frame — built from the frame's own
    # findings, anchored to the fact the frame is always read from.
    results: list[FrameResult] = []
    for frame in rs.frames:
        anchor = ANCHOR[frame]
        if anchor not in facts:
            raise ResolverError(f"{rs.id}: the ledger has no {anchor}, the "
                                f"anchor of the {frame} frame")
        mine = [f for f in findings if f.frame == frame]
        missing = tuple(sorted({f.values["missing"] for f in mine
                                if f.kind == MISSING}))
        real = [f for f in mine if f.kind != MISSING]
        support = sum(f.weight for f in real if f.kind == "support")
        strain = sum(f.weight for f in real if f.kind == "strain")
        weighed = [f for f in real if f.kind in BALANCE_KINDS and f.weight]
        dated = [f for f in real if f.kind in TIMING_KINDS]
        if rs.timing:
            tstatus = timing_status(real)
            status = "value" if dated else "silent"
            polarity = None
        else:
            tstatus = None
            status = "value" if weighed else "silent"
            polarity = frame_polarity(support, strain)
        # A silent frame says WHY in a code the narrator turns into words:
        # cited_only — rules fired and named what they found, at weight 0;
        # no_finding — no rule fired on this chart in this frame at all.
        reason = ""
        if status == "silent":
            reason = "cited_only" if real else "no_finding"
        fact_ids = tuple(sorted({anchor} | {fid for f in real
                                             for fid in f.fact_ids}))
        results.append(FrameResult(
            frame=frame, status=status, polarity=polarity, timing=tstatus,
            support=support, strain=strain,
            findings=tuple(f"{f.rule_id}/{f.slot}" for f in real),
            fact_ids=fact_ids, anchor=anchor, missing=missing, reason=reason))
    if {r.frame for r in results} != set(rs.frames):
        raise ResolverError(f"{rs.id}: a declared frame has no FrameResult")

    if rs.timing:
        verdict, disagreement, spoke = _timing_verdict(results)
    else:
        verdict, disagreement = frame_verdict(
            {r.frame: r.polarity for r in results})
        disagreement = tuple(disagreement)
        spoke = tuple(r.frame for r in results if r.polarity is not None)

    all_missing = tuple(sorted({m for r in results for m in r.missing}))
    return ResolverOutput(
        ruleset=rs.id, base=rs.base, timing=rs.timing,
        when=when.date().isoformat(), findings=tuple(findings),
        frames=tuple(results), verdict=verdict, disagreement=disagreement,
        spoke=spoke, balance=conditions.balance(findings),
        missing=all_missing, schools=schools.active())


def _timing_verdict(results) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """in_play | quiet | split | silent over the dated frames. Two frames
    that differ are a split by construction — the majority row cannot
    decide between two — and both are named."""
    spoke = tuple(r.frame for r in results if r.timing in ("in_play", "quiet"))
    states = {r.frame: r.timing for r in results if r.frame in spoke}
    if not states:
        return "silent", (), ()
    kinds = set(states.values())
    if len(kinds) == 1:
        return kinds.pop(), (), spoke
    return "split", tuple(sorted(states)), spoke
