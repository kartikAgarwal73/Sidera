"""Stage 1 — DETECT.

"Run every condition predicate over chart + pañcāṅga + gocara. Each returns
a hit with a weight."

`Conditions` is the read-only view a fragment predicate is handed. Every
method is a pure function of (chart, timeline, pañcāṅga, moment) — nothing
reads the clock, so a reading for any date is reproducible forever.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from engine import PLANETS, SIGNS, Chart, julian_day_ut, sidereal_positions
from pancanga import Pancanga
from transits import angular_distance, next_sign_ingress, sign_entry_before

SLOW = ("Saturn", "Jupiter", "Rahu", "Ketu")
BENEFIC = ("Jupiter", "Venus", "Mercury", "Moon")

# Gocara houses counted from the natal Moon.
CANDRA_FAVOURABLE = (1, 3, 6, 7, 10, 11)
CANDRA_TESTING = (4, 8, 12)

# Tithis traditionally read as lean for beginnings.
RIKTA_TITHIS = (4, 9, 14)
HARSH_YOGAS = ("Viṣkambha", "Atigaṇḍa", "Śūla", "Gaṇḍa", "Vyāghāta",
               "Vajra", "Vyatīpāta", "Parigha", "Vaidhṛti")

WINDOW_DAYS = 5  # "recently or imminently" for boundary conditions


@dataclass(frozen=True)
class Hit:
    """One condition that fired, with the fact that fired it."""

    fragment_id: str
    weight: int
    graha: str          # for tie-breaking by natural order
    fact: str           # the computed working, shown to the reader


@dataclass
class Conditions:
    """The facts a fragment predicate may ask about."""

    chart: Chart
    timeline: object            # VimshottariTimeline
    pancanga: Pancanga
    when: datetime
    person_key: str = ""
    _cache: dict = field(default_factory=dict, repr=False)

    # --- helpers ---------------------------------------------------------

    def _positions(self, at: datetime | None = None):
        at = at or self.when
        key = at.isoformat()
        if key not in self._cache:
            self._cache[key] = sidereal_positions(julian_day_ut(at))
        return self._cache[key]

    @property
    def natal_moon_sign(self) -> int:
        return self.chart.planets["Moon"].sign_index

    # --- weight 100: daśā boundaries -------------------------------------

    def dasa_boundary(self) -> tuple[str, str, datetime] | None:
        """('md'|'ad', lord, when) if a period turns within the window."""
        cur = self.timeline.at(self.when)
        if cur is None:
            return None
        md, ad = cur
        lo, hi = self.when - timedelta(days=WINDOW_DAYS), \
            self.when + timedelta(days=WINDOW_DAYS)
        if lo <= md.start <= hi or lo <= md.end <= hi:
            return ("md", md.lord, md.start if lo <= md.start <= hi else md.end)
        if lo <= ad.start <= hi or lo <= ad.end <= hi:
            return ("ad", ad.lord, ad.start if lo <= ad.start <= hi else ad.end)
        return None

    # --- weight 90: sāḍhe sātī phase -------------------------------------

    def sade_sati_phase_change(self) -> tuple[str, datetime] | None:
        """Saturn crossing into or out of the 12th/1st/2nd from the Moon."""
        moon = self.natal_moon_sign
        window = {(moon - 1) % 12, moon, (moon + 1) % 12}
        entered = sign_entry_before("Saturn", self.when)
        if entered and (self.when - entered).days <= WINDOW_DAYS:
            sign = self._positions()["Saturn"].sign_index
            if sign in window:
                return ("entered", entered)
        ing = next_sign_ingress("Saturn", self.when, max_days=WINDOW_DAYS + 1)
        if ing and (ing.when - self.when).days <= WINDOW_DAYS:
            here = self._positions()["Saturn"].sign_index
            if (here in window) != (ing.to_sign_index in window):
                return ("leaving" if here in window else "entering", ing.when)
        return None

    # --- weight 80: stations ---------------------------------------------

    def station(self) -> tuple[str, str, datetime] | None:
        """(planet, 'retrograde'|'direct', when) for a station in-window.

        Detected by a sign change in daily motion across the window — the
        nodes are excluded, their retrogression being perpetual."""
        before = self._positions(self.when - timedelta(days=WINDOW_DAYS))
        after = self._positions(self.when + timedelta(days=WINDOW_DAYS))
        for planet in PLANETS:
            if planet in ("Rahu", "Ketu", "Sun", "Moon"):
                continue
            b, a = before[planet].speed, after[planet].speed
            if b == 0 or a == 0 or (b < 0) == (a < 0):
                continue
            lo, hi = self.when - timedelta(days=WINDOW_DAYS), \
                self.when + timedelta(days=WINDOW_DAYS)
            while hi - lo > timedelta(hours=6):
                mid = lo + (hi - lo) / 2
                if (self._positions(mid)[planet].speed < 0) == (b < 0):
                    lo = mid
                else:
                    hi = mid
            return (planet, "direct" if a > 0 else "retrograde", hi)
        return None

    # --- weight 70: slow ingress ------------------------------------------

    def slow_ingress(self) -> tuple[str, str, datetime] | None:
        for planet in SLOW:
            entered = sign_entry_before(planet, self.when)
            if entered and (self.when - entered).days <= WINDOW_DAYS:
                return (planet, self._positions()[planet].sign, entered)
            ing = next_sign_ingress(planet, self.when,
                                    max_days=WINDOW_DAYS + 1)
            if ing and (ing.when - self.when).days <= WINDOW_DAYS:
                return (planet, ing.to_sign, ing.when)
        return None

    # --- weight 60: transit over natal lagna or Moon ----------------------

    def transit_over_natal(self, orb: float = 2.0):
        """(planet, point, orb) for a graha crossing the natal Lagna or Moon."""
        pos = self._positions()
        points = {"Lagna": self.chart.lagna.longitude,
                  "Moon": self.chart.planets["Moon"].longitude}
        best = None
        for planet in PLANETS:
            for label, lon in points.items():
                gap = angular_distance(pos[planet].longitude, lon)
                if gap <= orb and (best is None or gap < best[2]):
                    best = (planet, label, round(gap, 2))
        return best

    # --- weight 40: candra gocara ------------------------------------------

    def candra_house(self) -> int:
        moon_now = self._positions()["Moon"].sign_index
        return (moon_now - self.natal_moon_sign) % 12 + 1

    # --- weight 25: tithi and yoga quality ---------------------------------

    def tithi_index(self) -> int:
        return self.pancanga.tithi.index

    def tithi_within(self) -> int:
        return (self.pancanga.tithi.index - 1) % 15 + 1

    def yoga_name(self) -> str:
        return self.pancanga.yoga.name

    # --- weight 10: weekday lord vs daśā lord ------------------------------

    def weekday_lord(self) -> str:
        return self.pancanga.weekday_lord

    def dasa_lords(self) -> tuple[str, str] | None:
        cur = self.timeline.at(self.when)
        return (cur[0].lord, cur[1].lord) if cur else None

    # --- suppression flags --------------------------------------------------

    def flags(self) -> set[str]:
        out = set()
        if not getattr(self.chart.birth, "time_known", True):
            out.add("timeUnknown")
        return out


def detect(conditions: Conditions, fragments) -> list[Hit]:
    """Every fragment whose predicate fires, with its weight and its fact."""
    flags = conditions.flags()
    hits = []
    for frag in fragments:
        if set(frag.suppress_if) & flags:
            continue
        try:
            fired = frag.when(conditions)
        except Exception:
            fired = False
        if not fired:
            continue
        hits.append(Hit(fragment_id=frag.id, weight=frag.weight,
                        graha=frag.graha, fact=frag.fact(conditions)))
    return hits
