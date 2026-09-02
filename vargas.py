"""Divisional (varga) charts — D9 Navamsa and D10 Dasamsa, standard Parashari.

D9: each sign splits into 9 parts of 3°20′. Counting starts from the sign
itself for movable signs, the 9th from it for fixed, the 5th from it for dual —
which collapses to the classical formula: navamsa = (sign × 9 + part) mod 12.

D10: each sign splits into 10 parts of 3°. For odd signs (Aries, Gemini, …)
counting starts from the sign itself; for even signs (Taurus, Cancer, …) from
the 9th sign from it.

A planet is Vargottama when it occupies the same sign in D1 and D9.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine import PLANETS, SIGNS, Chart


def navamsa_sign(longitude: float) -> int:
    """D9 sign index for a sidereal longitude."""
    lon = longitude % 360.0
    sign = int(lon // 30)
    part = int((lon % 30.0) // (30.0 / 9.0))  # 0–8, each 3°20′
    return (sign * 9 + part) % 12


def dasamsa_sign(longitude: float) -> int:
    """D10 sign index for a sidereal longitude."""
    lon = longitude % 360.0
    sign = int(lon // 30)
    part = int((lon % 30.0) // 3.0)  # 0–9, each 3°
    offset = 0 if sign % 2 == 0 else 8  # odd signs from self, even from 9th
    return (sign + offset + part) % 12


_VARGA_FN = {"D9": navamsa_sign, "D10": dasamsa_sign}


@dataclass(frozen=True)
class VargaPosition:
    name: str
    sign_index: int
    house: int  # Whole Sign house from the divisional lagna, 1–12
    vargottama: bool = False  # same sign in D1 and D9 (set for D9 only)

    @property
    def sign(self) -> str:
        return SIGNS[self.sign_index]


@dataclass(frozen=True)
class VargaChart:
    varga: str  # "D9" or "D10"
    lagna_sign_index: int
    planets: dict[str, VargaPosition]

    @property
    def lagna_sign(self) -> str:
        return SIGNS[self.lagna_sign_index]

    @property
    def house_signs(self) -> dict[int, str]:
        return {
            h: SIGNS[(self.lagna_sign_index + h - 1) % 12] for h in range(1, 13)
        }

    @property
    def houses(self) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        for name in PLANETS:
            out[self.planets[name].house].append(name)
        return out


def varga_chart(chart: Chart, varga: str) -> VargaChart:
    """Divisional chart: every planet's divisional sign + house from the
    divisional lagna (Whole Sign)."""
    try:
        sign_fn = _VARGA_FN[varga]
    except KeyError:
        raise ValueError(f"Unsupported varga {varga!r}; supported: D9, D10")

    lagna_sign = sign_fn(chart.lagna.longitude)
    planets: dict[str, VargaPosition] = {}
    for name, pos in chart.planets.items():
        d_sign = sign_fn(pos.longitude)
        planets[name] = VargaPosition(
            name=name,
            sign_index=d_sign,
            house=(d_sign - lagna_sign) % 12 + 1,
            vargottama=(varga == "D9" and d_sign == pos.sign_index),
        )
    return VargaChart(varga=varga, lagna_sign_index=lagna_sign, planets=planets)


def navamsa(chart: Chart) -> VargaChart:
    return varga_chart(chart, "D9")


def dasamsa(chart: Chart) -> VargaChart:
    return varga_chart(chart, "D10")
