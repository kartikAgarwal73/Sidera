#!/usr/bin/env bash
#
# Build the PyJHora oracle fixture.
#
# Installs PyJHora into a scratch venv OUTSIDE this repository, runs it
# against the fictional fixture charts with the Lahiri ayanamsa pinned, and
# writes fixtures_pyjhora.json at the repo root. Only that JSON is committed.
#
#   ./tools/oracle/make_oracle.sh                 # venv in $TMPDIR
#   SIDERA_ORACLE_VENV=/some/path ./tools/oracle/make_oracle.sh
#
# PyJHora is AGPL-3.0. So is Sidera (pyswisseph forces it), so linking it
# would raise no licence question — the reason it stays outside the app is
# that an oracle sharing code with the thing it checks is not an oracle. See
# export_pyjhora.py and tools/oracle/README.md.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
VENV="${SIDERA_ORACLE_VENV:-${TMPDIR:-/tmp}/sidera-oracle-venv}"
OUT="${SIDERA_ORACLE_OUT:-$REPO/fixtures_pyjhora.json}"

case "$VENV" in
  "$REPO"|"$REPO"/*)
    echo "refusing to build the venv inside the repo ($VENV)." >&2
    echo "PyJHora and its GUI dependencies must not land in the tree." >&2
    exit 2 ;;
esac

# PyJHora's own requirements.txt pins PyQt6, img2pdf and geocoder's full
# stack. Only what the computation path actually imports is installed here;
# the GUI is never touched. Pinned, for the same reason requirements.txt is.
PYJHORA_VERSION="${PYJHORA_VERSION:-4.8.7}"
DEPS=(
  "PyJHora==${PYJHORA_VERSION}"
  "pyswisseph==2.10.3.2"     # same pin as the app, so the ephemeris matches
  "numpy==2.1.1"
  "pytz==2024.1"
  "python-dateutil"
  "scipy"
  "geocoder==1.38.1"
  "geopy==2.4.1"
  "requests==2.32.3"
  "timezonefinder==6.5.2"
  "reverse_geocode==1.6.6"
)

echo "==> scratch venv: $VENV"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
for dep in "${DEPS[@]}"; do
  echo "    installing $dep"
  "$VENV/bin/pip" -q --timeout 120 --retries 5 install "$dep"
done

# The birth records come from fixtures.py so there is ONE source of truth for
# them, and so a substituted SIDERA_FIXTURES cannot silently produce an
# oracle for a different chart than the suite runs against. Run with the
# REPO's python (which has no jhora on its path) — the export runs with the
# venv's python (which has no Sidera on its path). They meet only through
# this JSON file.
BIRTHS="$(mktemp)"
trap 'rm -f "$BIRTHS"' EXIT
( cd "$REPO" && python3 - "$BIRTHS" <<'PY'
import json, sys
import fixtures

def hours(tz: str) -> float:
    """fixtures.py stores '+05:30'; PyJHora wants 5.5."""
    sign = -1.0 if tz.strip().startswith("-") else 1.0
    hh, _, mm = tz.strip().lstrip("+-").partition(":")
    return sign * (int(hh) + int(mm or 0) / 60.0)

out = {}
for name in ("reference", "partner"):
    b = fixtures.birth(name)
    if not fixtures.is_built_in(name):
        raise SystemExit(
            f"fixture {name!r} has been substituted via SIDERA_FIXTURES. "
            "The committed oracle must describe the committed fictional "
            "charts only — refusing to export.")
    out[name] = {
        "year": b.year, "month": b.month, "day": b.day,
        "hour": b.hour, "minute": b.minute,
        "latitude": b.latitude, "longitude": b.longitude,
        "place": b.place, "tz": b.tz, "tz_hours": hours(b.tz),
    }
json.dump(out, open(sys.argv[1], "w"), indent=1, sort_keys=True)
print(f"    fixtures: {', '.join(sorted(out))}")
PY
)

echo "==> running the oracle"
"$VENV/bin/python" "$HERE/export_pyjhora.py" --births "$BIRTHS" --out "$OUT"

echo "==> done. Commit only: $(basename "$OUT")"
