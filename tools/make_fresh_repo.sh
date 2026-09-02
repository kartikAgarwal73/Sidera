#!/usr/bin/env bash
#
# Stage Sidera as a standalone repository with clean history.
#
# WHY A FRESH REPO AND NOT A RENAME
# The app currently lives in the vedic-astro/ subdirectory of a repository
# whose root holds unrelated files, and — the part that actually decides it —
# whose HISTORY contains the commissioner's real birth record. Five commits
# carry it. Removing it from the working tree does not remove it from a clone.
# Renaming the repo would publish that history. So the public repo starts
# from a single commit with no ancestry.
#
# The existing repository stays private and keeps the build log; nothing is
# deleted by this script.
#
# Usage:
#     tools/make_fresh_repo.sh [target-dir]      # default: ../sidera-public
#
# Then:
#     cd <target-dir>
#     git remote add origin https://github.com/<you>/sidera.git
#     git push -u origin main
#
# Render's Root Directory then stays blank — the app is at the root.

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-$(dirname "$APP_DIR")/sidera-public}"

if [ -e "$TARGET" ]; then
    echo "refusing to overwrite existing path: $TARGET" >&2
    exit 1
fi

echo "source: $APP_DIR"
echo "target: $TARGET"

# Copy the tracked app only — no .git, no caches, no local artefacts.
mkdir -p "$TARGET"
tar -C "$APP_DIR" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    -cf - . | tar -C "$TARGET" -xf -

cd "$TARGET"

# --- refuse to ship a repo that still carries a real birth record ----------
echo
echo "checking for personal data..."
# The scanners necessarily contain the patterns they search for, and
# PROGRESS.md documents them in prose — same exclusion the in-suite check
# uses (test_no_secrets_or_local_paths_in_source).
if grep -rIl --exclude-dir=data \
        --exclude=test_gates.py --exclude=test_hygiene.py \
        --exclude=conftest.py --exclude=PROGRESS.md \
        --exclude=make_fresh_repo.sh \
        -E '(/Users/|C:\\Users|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY)' . ; then
    echo "ABORT: secrets or absolute local paths found above." >&2
    exit 1
fi
if [ -n "$(find . -name '*.se1' -o -name '*.se2')" ]; then
    echo "ABORT: ephemeris data files found; they are not meant to ship." >&2
    exit 1
fi

# Retired personal data — a DIFFERENT question from "no secrets", and the
# one that actually bit. The first public push of this repo leaked a birth
# record: the secrets grep above passed, but PLAN.md still carried the
# Phase 1/2/3 gate values, and a full natal chart reconstructs a birth
# moment as surely as the birth line does. The repo had to be deleted and
# recreated, because a force-push does NOT unserve a published commit.
#
# The patterns live OUTSIDE this repository, in a file you point
# SIDERA_REDACTION_PATTERNS at — one grep -E pattern per line, blank lines
# and #-comments ignored. They are deliberately not hardcoded here: a
# scanner that carries the retired values in plaintext publishes them the
# moment it ships, which defeats the whole exercise.
#
#     SIDERA_REDACTION_PATTERNS=~/.sidera-retired tools/make_fresh_repo.sh
#
if [ -n "${SIDERA_REDACTION_PATTERNS:-}" ]; then
    if [ ! -r "$SIDERA_REDACTION_PATTERNS" ]; then
        echo "ABORT: SIDERA_REDACTION_PATTERNS set but unreadable: $SIDERA_REDACTION_PATTERNS" >&2
        exit 1
    fi
    leaked=0
    while IFS= read -r pat; do
        case "$pat" in ''|'#'*) continue ;; esac
        # data/ holds the public GeoNames extract — 32k world cities with
        # city-centre coordinates, not anyone's birth record.
        hits=$(grep -rIl --exclude-dir=data -E "$pat" . 2>/dev/null || true)
        if [ -n "$hits" ]; then
            echo "  LEAK: pattern matched in: $hits" >&2
            leaked=1
        fi
    done < "$SIDERA_REDACTION_PATTERNS"
    if [ "$leaked" -ne 0 ]; then
        echo "ABORT: retired personal data found above. Redact before publishing." >&2
        exit 1
    fi
    echo "clean (incl. $(grep -cvE '^\s*(#|$)' "$SIDERA_REDACTION_PATTERNS") retired-data patterns)."
else
    echo "clean (secrets only)."
    echo
    echo "  NOTE: no SIDERA_REDACTION_PATTERNS file given, so retired personal" >&2
    echo "  data was NOT checked. That omission is how this repo leaked a birth" >&2
    echo "  record on its first public push. If any fixture has ever been" >&2
    echo "  retired, supply the file and re-run." >&2
fi

# --- the suite must pass from the new root --------------------------------
echo
echo "running the gate suite from the new root..."
python -m pytest -q

git init -q -b main
git add .
git commit -q -m "Sidera: initial public release

A sidereal Vedic astrology app that shows its computation: every reading
expands into the placement it came from, the classical rule applied, and a
confidence tag.

History starts here deliberately. The build history lives in a private
repository and contains a real birth record, so it is not published. The
committed verification fixtures are fictional; see fixtures.py."

echo
echo "done — $(git rev-list --count HEAD) commit, $(git ls-files | wc -l | tr -d ' ') files"
echo
echo "next:"
echo "    cd $TARGET"
echo "    git remote add origin https://github.com/<you>/sidera.git"
echo "    git push -u origin main"
