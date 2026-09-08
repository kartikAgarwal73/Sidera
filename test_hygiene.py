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
REQUIREMENTS_DEV = HERE / "requirements-dev.txt"

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
    regression. Every requirement carries an exact version — test-only ones
    too, since a test dependency that drifts fails the same way."""
    for path in (REQUIREMENTS, REQUIREMENTS_DEV):
        lines = [ln.strip() for ln in path.read_text().splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
        assert lines, f"{path.name} is empty"
        unpinned = [ln for ln in lines if "==" not in ln]
        assert not unpinned, f"unpinned in {path.name}: {unpinned}"
    # The server install must not carry the browser gate's 140 MB. Comments
    # may name it — the point is that pip must not be asked to install it.
    installed = [ln.strip() for ln in REQUIREMENTS.read_text().splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
    assert not any("playwright" in ln for ln in installed), (
        "playwright belongs in requirements-dev.txt; the running app never "
        "imports it and a deploy should not download it")


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


# --- the oracle stays an oracle ---------------------------------------------

ORACLE_JSON = HERE / "fixtures_pyjhora.json"
APP_MODULES = (
    "app.py", "agent.py", "ask.py", "chartfacts.py", "dashas.py",
    "doshas.py", "engine.py", "explain.py", "fixtures.py", "gunamilan.py",
    "lessons.py", "pancanga.py", "rulelib.py", "transits.py", "vargas.py",
    "yogas.py",
)


@pytest.mark.hygiene
def test_no_app_module_imports_the_oracle():
    """PyJHora is a second opinion, not a dependency.

    The value of `fixtures_pyjhora.json` is that PyJHora shares no line of
    interpretation code with Sidera. If the app imported `jhora`, an
    agreement would prove only that a function agrees with itself — and the
    deploy would grow a GUI toolkit. Neither is acceptable, so it is checked
    rather than remembered.
    """
    offenders = []
    for name in APP_MODULES + ("reading", "tools/refresh_audit_counts.py"):
        path = HERE / name
        files = sorted(path.rglob("*.py")) if path.is_dir() else [path]
        for f in files:
            if not f.exists():
                continue
            text = f.read_text(encoding="utf-8")
            if re.search(r"^\s*(?:import|from)\s+jhora\b", text, re.M):
                offenders.append(str(f.relative_to(HERE)))
    assert not offenders, (
        f"{offenders} import the oracle package. PyJHora must stay outside "
        "the app: see tools/oracle/README.md.")


@pytest.mark.hygiene
def test_oracle_is_not_installed_in_the_app_environment():
    """The suite must be able to run without PyJHora present.

    If it ever became importable here, a test could start depending on it
    silently and the fence above would be the only thing left holding.
    """
    import importlib.util
    assert importlib.util.find_spec("jhora") is None, (
        "PyJHora is installed in the app environment. It belongs in the "
        "scratch venv built by tools/oracle/make_oracle.sh, outside the "
        "repo.")


@pytest.mark.hygiene
def test_oracle_fixture_is_committed_and_declares_its_settings():
    """The two settings that make the file trustworthy are recorded IN it.

    PyJHora defaults to the True Pushya ayanamsa and the true node; Sidera
    uses Lahiri and the mean node. A file that does not say which it used is
    not evidence of anything.
    """
    import json
    assert ORACLE_JSON.exists(), (
        "fixtures_pyjhora.json is missing — regenerate with "
        "tools/oracle/make_oracle.sh")
    data = json.loads(ORACLE_JSON.read_text(encoding="utf-8"))
    assert data["settings"]["ayanamsa_mode"] == "LAHIRI"
    assert data["settings"]["node_mode"] == "mean"
    assert data["oracle"]["package"] == "PyJHora"
    assert data["oracle"]["licence"] == "AGPL-3.0"
    assert data["oracle"]["version"] != "unknown"
    for name, chart in data["charts"].items():
        ayanamsa = chart["ayanamsa"]
        assert ayanamsa["mode"] == "LAHIRI", name
        # The proof that the default was overridden: the file carries the
        # value it was NOT computed with, and the two are far apart.
        assert ayanamsa["pyjhora_default_mode"] == "TRUE_PUSHYA", name
        assert abs(ayanamsa["difference_arcsec"]) > 3000, name
        assert chart["nodes"]["used"] == "mean", name


@pytest.mark.hygiene
def test_licence_is_agpl_because_pyswisseph_is():
    """AGPL is inherited, not chosen. Pinning it here means a future session
    cannot quietly relicense while still linking pyswisseph."""
    licence = (HERE / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in licence
    assert "Version 3, 19 November 2007" in licence
    # Section 13 is the reason this licence is not interchangeable with GPL
    # for a web app, and the reason the footer carries a Source link.
    assert "13. Remote Network Interaction" in licence
    readme = (HERE / "README.md").read_text(encoding="utf-8")
    assert "AGPL-3.0" in readme and "pyswisseph" in readme
    # §13 in practice: a network user must be able to REACH the source from
    # the running app. A public repo the page never points at does not do it.
    page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
    footer = page[page.index("<footer"):page.index("</footer>")]
    assert "AGPL-3.0" in footer, "the footer must name the licence"
    assert re.search(r'href="https://github\.com/\S+"[^>]*>\s*Source\s*<',
                     footer), "the footer must carry a Source link (AGPL §13)"
