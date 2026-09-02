"""Guards on the gates — memory hygiene for a multi-session build.

`test_gates.py` protects the app. This file protects the protection:

1. Every test declares where its expected values came from (conftest.py),
   so a future session can tell "the code regressed" from "my expectation
   was wrong" without reconstructing eight months of context.
2. The numbers quoted in the conformance audit are checked against reality,
   so the audit cannot quietly drift the way it already did once (it claimed
   125 tests while the suite stood at 144).
3. Dependencies are pinned, so an environment collapse cannot masquerade as
   a code regression — which also already happened once.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

import conftest as prov

HERE = Path(__file__).parent
AUDIT = HERE / "ui-design" / "FRAMEWORK-AUDIT.md"
REQUIREMENTS = HERE / "requirements.txt"

COUNTS_BLOCK = re.compile(
    r"<!-- HYGIENE-COUNTS.*?-->(.*?)<!-- /HYGIENE-COUNTS -->", re.S)


def collected_provenance() -> dict[str, int]:
    """Run collection in a subprocess and tally declared provenance."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "test_gates.py", "--collect-only", "-q"],
        cwd=HERE, capture_output=True, text=True, check=False).stdout
    tally = {name: 0 for name in prov.PROVENANCE_CLASSES}
    tally["undeclared"] = 0
    for line in out.splitlines():
        if "::" not in line:
            continue
        parts = line.strip().split("::")
        if len(parts) < 3:
            continue
        cls, func = parts[1], parts[2].split("[")[0]
        declared = prov.provenance_for(cls, func)
        tally[declared[0] if declared else "undeclared"] += 1
    return tally


@pytest.fixture(scope="module")
def tally():
    return collected_provenance()


@pytest.mark.hygiene
def test_every_test_declares_its_provenance(tally):
    """A test whose expected values have no declared origin is a test nobody
    can safely interpret later. Register it in conftest.py."""
    assert tally["undeclared"] == 0, (
        f"{tally['undeclared']} test(s) have no provenance declared. Add them "
        "to CLASS_DEFAULT or OVERRIDE in conftest.py — see the module "
        "docstring for what the three classes mean."
    )


@pytest.mark.hygiene
def test_provenance_registry_has_no_dead_entries():
    """Overrides for tests that no longer exist are stale memory too."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "test_gates.py", "--collect-only", "-q"],
        cwd=HERE, capture_output=True, text=True, check=False).stdout
    live = set()
    for line in out.splitlines():
        parts = line.strip().split("::")
        if len(parts) >= 3:
            live.add(f"{parts[1]}::{parts[2].split('[')[0]}")
    dead = sorted(k for k in prov.OVERRIDE if k not in live)
    assert not dead, f"conftest.OVERRIDE names tests that no longer exist: {dead}"


@pytest.mark.hygiene
def test_every_declaration_names_a_real_class_and_source():
    for key, (cls, source) in list(prov.OVERRIDE.items()) + [
            (k, v) for k, v in prov.CLASS_DEFAULT.items()]:
        assert cls in prov.PROVENANCE_CLASSES, f"{key}: unknown class {cls!r}"
        assert source and len(source) > 8, f"{key}: source note too thin"


@pytest.mark.hygiene
def test_audit_counts_match_reality(tally):
    """The audit's numbers are generated facts, not prose. If this fails,
    run `python tools/refresh_audit_counts.py` — do not hand-edit."""
    assert AUDIT.exists(), "conformance audit is missing"
    block = COUNTS_BLOCK.search(AUDIT.read_text(encoding="utf-8"))
    assert block, (
        "the audit has no HYGIENE-COUNTS block — regenerate it with "
        "tools/refresh_audit_counts.py"
    )
    claimed = {m.group(1).strip("`* "): int(m.group(2)) for m in
               re.finditer(r"\|\s*([`*\w]+)\s*\|\s*(\d+)\s*\|", block.group(1))}
    total = sum(tally[c] for c in prov.PROVENANCE_CLASSES)
    expected = {c: tally[c] for c in prov.PROVENANCE_CLASSES}
    expected["total"] = total
    assert claimed == expected, (
        f"audit claims {claimed}, reality is {expected}. "
        "Run: python tools/refresh_audit_counts.py"
    )


@pytest.mark.hygiene
def test_dependencies_are_pinned():
    """An unpinned environment lets a dependency change look like a code
    regression. Every runtime requirement carries an exact version."""
    lines = [ln.strip() for ln in REQUIREMENTS.read_text().splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    assert lines, "requirements.txt is empty"
    unpinned = [ln for ln in lines if "==" not in ln]
    assert not unpinned, f"unpinned requirements: {unpinned}"


@pytest.mark.hygiene
def test_characterization_share_is_declared_honestly(tally):
    """Not a threshold to game — a tripwire. If characterization tests come
    to dominate, the suite is mostly defending its own past behaviour, and
    the audit's 'what protects us' section needs rewriting to say so."""
    total = sum(tally[c] for c in prov.PROVENANCE_CLASSES)
    share = tally["characterization"] / total
    assert share < 0.60, (
        f"characterization tests are {share:.0%} of the suite. That is not a "
        "failure of the code — it is a signal that most of what the suite "
        "guarantees is continuity, not correctness. Add externally anchored "
        "cases, or update the audit to state the ratio plainly."
    )
