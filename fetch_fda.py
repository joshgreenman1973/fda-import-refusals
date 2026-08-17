#!/usr/bin/env python3
"""Page the FDA Data Dashboard import_refusals endpoint month by month.

Credentials come from the environment (FDA_USER / FDA_KEY) and are never written
to disk. Output: fda_refusals.jsonl (one refusal per line).
Fails loudly if a month returns nothing while neighbouring months have data.
"""
import json, os, sys, time, urllib.request, datetime

USER = os.environ["FDA_USER"]
KEY = os.environ["FDA_KEY"]
URL = "https://api-datadashboard.fda.gov/v1/import_refusals"
PAGE = 5000
COLS = ["FirmName", "CountryName", "ProductCodeDescription", "RefusalCharges",
        "RefusalDate", "IndustryCodeDescription", "City", "State",
        "DistrictDescription", "ProductCategory", "ProductCode", "FEINumber",
        "ShipmentID", "FDASampleAnalysis", "PrivateLabAnalysis"]

START = sys.argv[1] if len(sys.argv) > 1 else "2002-01"
END = sys.argv[2] if len(sys.argv) > 2 else "2026-08"
OUT = sys.argv[3] if len(sys.argv) > 3 else "fda_refusals.jsonl"


def post(body, tries=4):
    data = json.dumps(body).encode()
    for a in range(tries):
        req = urllib.request.Request(URL, data=data, headers={
            "Content-Type": "application/json",
            "Authorization-User": USER,
            "Authorization-Key": KEY})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read().decode())
            if isinstance(d, list):
                raise RuntimeError(str(d)[:200])
            return d.get("result") or []
        except Exception as e:
            if a == tries - 1:
                raise
            time.sleep(3 * (a + 1))


def months(a, b):
    y, m = int(a[:4]), int(a[5:7])
    ey, em = int(b[:4]), int(b[5:7])
    while (y, m) <= (ey, em):
        last = (datetime.date(y + (m == 12), (m % 12) + 1, 1) - datetime.timedelta(days=1)).day
        yield "%04d-%02d-01" % (y, m), "%04d-%02d-%02d" % (y, m, last)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def main():
    seen, total, empty_run = set(), 0, 0
    out = open(OUT, "w", encoding="utf-8")
    for f, t in months(START, END):
        got, start = 0, 1
        while True:
            rows = post({"start": str(start), "rows": str(PAGE),
                         "sort": "RefusalDate", "sortorder": "ASC",
                         "filters": {"RefusalDateFrom": [f], "RefusalDateTo": [t]},
                         "columns": COLS})
            for r in rows:
                k = r.get("ShipmentID")
                if k and k in seen:
                    continue
                if k:
                    seen.add(k)
                out.write(json.dumps(r, separators=(",", ":")) + "\n")
                got += 1
            if len(rows) < PAGE:
                break
            start += PAGE
        total += got
        print("%s  %6d  (running %d)" % (f[:7], got, total), flush=True)
        empty_run = empty_run + 1 if got == 0 else 0
        if empty_run >= 18:
            break                      # 18 straight empty months = past the data
    out.close()
    if total == 0:
        sys.exit("FAIL: fetched zero refusals")
    print("DONE %d refusals -> %s" % (total, OUT))


if __name__ == "__main__":
    main()
