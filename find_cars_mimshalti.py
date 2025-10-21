import json
from collections import Counter, defaultdict
from datetime import datetime
import requests


def _safe_month(value: str) -> str:
    """
    Normalize moed_aliya_lakvish to YYYY-MM; return 'UNKNOWN' if invalid.
    """
    if not value or not isinstance(value, str):
        return "UNKNOWN"
    parts = value.split('-')
    if len(parts) != 2:
        return "UNKNOWN"
    year, month = parts
    if not (year.isdigit() and month.isdigit()):
        return "UNKNOWN"
    try:
        dt = datetime(int(year), int(month), 1)
        return f"{dt.year:04d}-{dt.month:02d}"
    except ValueError:
        return "UNKNOWN"


def main():
    year = "2022"
    kod_degem = "255"
    kod_tozar = "416"

    url = "https://data.gov.il/api/3/action/datastore_search"
    params = {
        'resource_id': '053cea08-09bc-40ec-8f7a-156f0677aff3',
        'limit': 99999999,
        'filters': json.dumps({
            'shnat_yitzur': year,
            'degem_cd': kod_degem,
            'tozeret_cd': kod_tozar,
        })
    }

    response = requests.get(url, params=params, timeout=120)
    response.raise_for_status()
    data = response.json()
    records = data.get("result", {}).get("records", [])

    # Normalize and enrich fields
    for r in records:
        r["_baalut"] = (r.get("baalut") or "").strip() or "UNKNOWN"
        r["_moed"] = _safe_month(r.get("moed_aliya_lakvish"))

    # Sort records chronologically by month then (optionally) license plate
    records.sort(key=lambda x: (
        x["_moed"] if x["_moed"] != "UNKNOWN" else "9999-99",
        x.get("mispar_rechev", "")
    ))

    total = len(records)
    baalut_counter = Counter(r["_baalut"] for r in records)

    # Build nested month counters per baalut
    baalut_month_counters: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        baalut_month_counters[r["_baalut"]][r["_moed"]] += 1

    # Top-level baalut statistics
    print("\nBaalut Statistics:")
    for baalut, count in baalut_counter.most_common():
        pct = (count / total * 100) if total else 0
        print(f"{baalut}: {count} vehicles ({pct:.2f}%)")

    # Nested month breakdown per baalut
    print("\nBaalut -> moed_aliya_lakvish breakdown:")
    for baalut, count in baalut_counter.most_common():
        print(f"\n{baalut} (total {count}):")
        month_counter = baalut_month_counters[baalut]

        # Sort months chronologically; UNKNOWN last
        def month_sort_key(m):
            if m == "UNKNOWN":
                return ("9999", "99")
            y, mth = m.split('-')
            return (y, mth)

        for month in sorted(month_counter.keys(), key=month_sort_key):
            m_count = month_counter[month]
            m_pct = (m_count / count * 100) if count else 0
            print(f"  {month}: {m_count} ({m_pct:.2f}%)")

    # (Optional) iterate records if needed
    for r in records:
        print(f'car model: {r.get("kinuy_mishari")}, year: {r.get("shnat_yitzur")}, '
              f'moed_aliya_lakvish: {r.get("moed_aliya_lakvish")}, license_plate: {r.get("mispar_rechev")}, '
              f'tokef_dt: {r.get("tokef_dt")}, baalut: {r.get("baalut")}, ramat_gimur: {r.get("ramat_gimur")}')

if __name__ == '__main__':
    main()