"""Regenerate the provenance counts block in ui-design/FRAMEWORK-AUDIT.md.

The audit's prose is hand-written; its numbers are not. Run this after adding
or removing tests — `test_hygiene.py` fails until the block matches reality.

    python tools/refresh_audit_counts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from test_hygiene import AUDIT, COUNTS_BLOCK, collected_provenance  # noqa: E402
import conftest as prov  # noqa: E402

BLURB = {
    "external": "anchored outside this build — a red one means the code is wrong",
    "invariant": "true by definition or product rule — a red one means the code is wrong",
    "characterization": "froze observed output — protects continuity, not correctness",
}


def render(tally: dict[str, int]) -> str:
    total = sum(tally[c] for c in prov.PROVENANCE_CLASSES)
    rows = "\n".join(
        f"| `{c}` | {tally[c]} | {tally[c] / total:.0%} | {BLURB[c]} |"
        for c in prov.PROVENANCE_CLASSES)
    return (
        "\n| Provenance | Tests | Share | What a failure means |\n"
        "|---|---|---|---|\n"
        f"{rows}\n"
        f"| **total** | {total} | | |\n"
    )


def main() -> None:
    tally = collected_provenance()
    if tally["undeclared"]:
        raise SystemExit(
            f"{tally['undeclared']} test(s) undeclared — register them in "
            "conftest.py first.")
    text = AUDIT.read_text(encoding="utf-8")
    block = render(tally)
    if COUNTS_BLOCK.search(text):
        text = COUNTS_BLOCK.sub(
            lambda _: f"<!-- HYGIENE-COUNTS: generated, do not hand-edit -->"
                      f"{block}<!-- /HYGIENE-COUNTS -->", text, count=1)
    else:
        text += ("\n## Test provenance (generated)\n\n"
                 "<!-- HYGIENE-COUNTS: generated, do not hand-edit -->"
                 f"{block}<!-- /HYGIENE-COUNTS -->\n")
    AUDIT.write_text(text, encoding="utf-8")
    print("audit counts refreshed:",
          {c: tally[c] for c in prov.PROVENANCE_CLASSES})


if __name__ == "__main__":
    main()
