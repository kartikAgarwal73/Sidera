"""Build the bundled offline city dataset (data/cities.json).

Sources (fetched at BUILD time only — the app itself makes no network calls):
- geonamescache (PyPI) — GeoNames cities15000: name, lat/lon, country code,
  population, IANA timezone, admin1 code. Data © GeoNames, CC BY 4.0.
- dr5hn/countries-states-cities-database states.json — admin1/region display
  names, joined via FIPS code (GeoNames admin1 codes are FIPS for most
  countries, ISO/postal for a few — both are tried). Licence: ODbL.

Output row: [name, region, country, lat, lon, iana_tz, population]
Run: python data/build_cities.py path/to/states.json
"""
import json
import sys
import unicodedata

import geonamescache


def ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def main(states_path: str, out_path: str = "data/cities.json") -> None:
    gc = geonamescache.GeonamesCache()
    countries = {cc: c["name"] for cc, c in gc.get_countries().items()}

    # GeoNames admin1 codes are FIPS for most countries, so FIPS gets
    # absolute priority; ISO/postal suffixes fill gaps (e.g. US 'CA') in a
    # second pass only where no FIPS claim exists — the two systems collide
    # on bare numerals (ISO JP-40 is Fukuoka while FIPS JP/40 is Tokyo).
    with open(states_path, encoding="utf-8") as fh:
        states = json.load(fh)
    regions: dict[tuple[str, str], str] = {}
    for st in states:
        if st.get("fips_code"):
            regions.setdefault((st["country_code"], st["fips_code"]),
                               st["name"])
    for st in states:
        iso = (st.get("iso3166_2") or "").split("-")[-1]
        if iso:
            regions.setdefault((st["country_code"], iso), st["name"])

    rows = []
    for c in gc.get_cities().values():
        cc = c["countrycode"]
        region = regions.get((cc, c.get("admin1code", "")), "")
        rows.append([
            c["name"], region, countries.get(cc, cc),
            round(c["latitude"], 5), round(c["longitude"], 5),
            c["timezone"], c["population"],
        ])
    rows.sort(key=lambda r: -r[6])  # busiest first — natural ranking order

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(rows)} cities → {out_path}")


if __name__ == "__main__":
    main(sys.argv[1])
