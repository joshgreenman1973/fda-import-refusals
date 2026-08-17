#!/usr/bin/env python3
"""Build web data from the fetched FDA import refusal history.

Inputs : fda_refusals.jsonl (525k+ refusals, 2002-2026)
         charges.csv        (FDA's own ASC_ID -> charge statement crosswalk)
Output : out_fda/*.json
"""
import json, csv, os, sys, collections, re

OUT = "out_fda"
os.makedirs(OUT, exist_ok=True)

# ---- charge dictionary ----------------------------------------------------
charges = {}
for r in csv.DictReader(open("charges.csv", encoding="utf-8-sig")):
    charges[r["ASC_ID"].strip()] = {
        "code": r["CHRG_CODE"].strip(),
        "text": re.sub(r"\s+", " ", r["CHRG_STMNT_TEXT"]).strip(),
        "section": r["SCTN_NAME"].strip(),
    }
if not charges:
    sys.exit("FAIL: no charge codes loaded")

by_year = collections.Counter()
by_ym = collections.Counter()
by_country = collections.Counter()
by_country_year = collections.defaultdict(collections.Counter)
by_charge = collections.Counter()
by_charge_year = collections.defaultdict(collections.Counter)
by_industry = collections.Counter()
by_district = collections.Counter()
by_category = collections.Counter()
by_product = collections.Counter()
firms = collections.Counter()
firm_meta = {}
country_charge = collections.defaultdict(collections.Counter)
unknown_codes = collections.Counter()

recent = []
RECENT_FROM = "2025-09-01"

n = 0
for line in open("fda_refusals.jsonl", encoding="utf-8"):
    r = json.loads(line)
    n += 1
    d = (r.get("RefusalDate") or "")[:10]
    y = d[:4]
    if y:
        by_year[y] += 1
        by_ym[d[:7]] += 1
    c = (r.get("CountryName") or "Unknown").strip()
    by_country[c] += 1
    if y:
        by_country_year[c][y] += 1
    ind = (r.get("IndustryCodeDescription") or "").strip()
    if ind:
        by_industry[ind] += 1
    dist = (r.get("DistrictDescription") or "").strip()
    if dist:
        by_district[dist] += 1
    cat = (r.get("ProductCategory") or "").strip()
    if cat:
        by_category[cat] += 1
    prod = (r.get("ProductCodeDescription") or "").strip()
    if prod:
        by_product[prod] += 1
    fn = (r.get("FirmName") or "").strip()
    if fn:
        firms[(fn, c)] += 1
        firm_meta[(fn, c)] = (r.get("City") or "").strip()

    codes = [x.strip() for x in (r.get("RefusalCharges") or "").split(",") if x.strip()]
    for code in codes:
        by_charge[code] += 1
        if y:
            by_charge_year[code][y] += 1
        country_charge[c][code] += 1
        if code not in charges:
            unknown_codes[code] += 1

    if d >= RECENT_FROM:
        recent.append({
            "d": d, "f": fn, "c": c, "ci": (r.get("City") or "").strip(),
            "p": prod, "i": ind, "cat": cat,
            "ds": dist, "ch": codes, "s": (r.get("ShipmentID") or "").strip(),
        })
    if n % 100000 == 0:
        print("  ...", n, file=sys.stderr, flush=True)

if n == 0:
    sys.exit("FAIL: no refusal rows read")

years = sorted(by_year)
recent.sort(key=lambda r: r["d"], reverse=True)

charge_out = []
for code, cnt in by_charge.most_common():
    info = charges.get(code)
    charge_out.append({
        "id": code, "n": cnt,
        "code": info["code"] if info else None,
        "text": info["text"] if info else None,
        "section": info["section"] if info else None,
        "yr": dict(by_charge_year[code]),
    })

meta = {
    "source": "FDA Data Dashboard, import_refusals endpoint",
    "source_url": "https://datadashboard.fda.gov/oii/cd/imprefusals.htm",
    "charge_source": "https://datadashboard.fda.gov/oii/download/ACT_SECTION_CHARGES.CSV",
    "records": n,
    "date_min": min(by_ym) if by_ym else None,
    "date_max": max(by_ym) if by_ym else None,
    "countries": len(by_country),
    "charge_codes_used": len(by_charge),
    "charge_codes_known": sum(1 for c in by_charge if c in charges),
    "charge_codes_unknown": len(unknown_codes),
    "unknown_code_hits": sum(unknown_codes.values()),
    "recent_from": RECENT_FROM,
    "recent_count": len(recent),
    "firms": len(firms),
    "years": years,
}

agg = {
    "year": dict(by_year),
    "ym": dict(sorted(by_ym.items())),
    "country": by_country.most_common(),
    "country_year": {k: dict(v) for k, v in by_country_year.items()},
    "industry": by_industry.most_common(60),
    "district": by_district.most_common(40),
    "category": by_category.most_common(),
    "product": by_product.most_common(120),
}

top_firms = [{"f": f, "c": c, "ci": firm_meta[(f, c)], "n": cnt}
             for (f, c), cnt in firms.most_common(400)]


def dump(name, obj):
    p = os.path.join(OUT, name)
    json.dump(obj, open(p, "w"), separators=(",", ":"))
    return os.path.getsize(p)


sizes = {
    "meta.json": dump("meta.json", meta),
    "agg.json": dump("agg.json", agg),
    "charges.json": dump("charges.json", charge_out),
    "firms.json": dump("firms.json", top_firms),
    "recent.json": dump("recent.json", recent),
}
print("\nrows=%d  countries=%d  charges used=%d (unknown %d)  recent=%d"
      % (n, len(by_country), len(by_charge), len(unknown_codes), len(recent)), file=sys.stderr)
print("dates %s .. %s" % (meta["date_min"], meta["date_max"]), file=sys.stderr)
for k, v in sizes.items():
    print("  %-14s %7.2f MB" % (k, v / 1e6), file=sys.stderr)
print("\ntop charges:", file=sys.stderr)
for c in charge_out[:8]:
    print("   %-6s %-12s %7d  %s" % (c["id"], c["code"], c["n"], (c["text"] or "")[:70]), file=sys.stderr)
