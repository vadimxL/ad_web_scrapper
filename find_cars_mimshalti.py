import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, TypedDict, List, Dict, Optional
import requests
import requests_cache  # added


requests_cache.install_cache("mileage_http_cache", expire_after=3600)

DATAGOV_URL = "https://data.gov.il/api/3/action/datastore_search"
RESOURCE_ID_VEHICLES = "053cea08-09bc-40ec-8f7a-156f0677aff3"
RESOURCE_ID_MILEAGE = "56063a99-8a3e-4ff4-912e-5966c0279bad"
RESOURCE_ID_OWNERSHIP = "bb2355dc-9ec7-4f06-9c3f-3344672171da"  # ownership history (multiple entries per plate)

# Raw record as returned by the vehicles API (subset used)
class RawVehicleRecord(TypedDict, total=False):
    baalut: str
    moed_aliya_lakvish: str
    mispar_rechev: str
    shnat_yitzur: str
    tokef_dt: str  # added

# Enriched record after normalization
class VehicleRecord(RawVehicleRecord, total=False):
    _baalut: str
    _moed: str

# Mileage record from mileage API (subset used)
class MileageRecord(TypedDict, total=False):
    mispar_rechev: str
    kilometer_test_aharon: str

# Ownership record from ownership history API (subset used)
class OwnershipRecord(TypedDict, total=False):
    _id: int
    mispar_rechev: str | int
    baalut_dt: str | int  # raw date value from API (keep original)
    baalut: str
    rank: float


def _safe_month(value: str) -> str:
    """Normalize moed_aliya_lakvish to YYYY-MM; return 'UNKNOWN' if invalid."""
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


def enrich_vehicle_record(raw: RawVehicleRecord) -> VehicleRecord:
    """Produce an enriched VehicleRecord from a raw API record."""
    vr: VehicleRecord = raw.copy()  # type: ignore[assignment]
    vr["_baalut"] = (raw.get("baalut") or "").strip() or "UNKNOWN"
    vr["_moed"] = _safe_month(raw.get("moed_aliya_lakvish", ""))
    return vr


def normalize_vehicle_records(raw_records: List[RawVehicleRecord]) -> List[VehicleRecord]:
    """Normalize raw vehicle records: enrich & sort."""
    enriched: List[VehicleRecord] = [enrich_vehicle_record(r) for r in raw_records]
    sort_vehicle_records(enriched)
    return enriched


def fetch_vehicle_records(year: str, kod_degem: str, kod_tozar: str, session: Optional[requests.Session] = None) -> List[VehicleRecord]:
    """Fetch and normalize vehicle records from Data.gov.il.

    Args:
        year: Production year filter (shnat_yitzur).
        kod_degem: Model code (degem_cd).
        kod_tozar: Manufacturer code (tozeret_cd).
        session: Optional requests session (cached / mocked).

    Returns:
        List of enriched VehicleRecord dicts with _baalut and _moed fields populated.
    """
    req = session or requests
    params: Dict[str, Any] = {
        "resource_id": RESOURCE_ID_VEHICLES,
        "limit": 99999999,  # upstream large value; consider paging if becomes problematic
        "filters": json.dumps({
            "shnat_yitzur": year,
            "degem_cd": kod_degem,
            "tozeret_cd": kod_tozar,
        })
    }
    response = req.get(DATAGOV_URL, params=params, timeout=120)
    response.raise_for_status()
    data: Dict[str, Any] = response.json()
    raw_records: List[RawVehicleRecord] = data.get("result", {}).get("records", [])  # type: ignore[assignment]
    return normalize_vehicle_records(raw_records)


def sort_vehicle_records(records: List[VehicleRecord]) -> None:
    """In-place sort of vehicle records chronologically by _moed then license plate.
    UNKNOWN months are placed last.
    """
    records.sort(key=lambda x: (
        x.get("_moed") if x.get("_moed") != "UNKNOWN" else "9999-99",
        x.get("mispar_rechev", "") or ""
    ))


def fetch_mileage_records(plate_list: List[str], batch_size: int = 100, session: Optional[requests.Session] = None) -> Dict[str, MileageRecord]:
    """Fetch mileage records in batches to avoid overly long URLs.

    Args:
        plate_list: License plates to query.
        batch_size: Batch size for each API call.
        session: Optional requests session (cached / mocked).

    Returns:
        Mapping from license plate to its mileage record dict.
    """
    mileage_map: Dict[str, MileageRecord] = {}
    if not plate_list:
        return mileage_map

    req = session or requests
    for i in range(0, len(plate_list), batch_size):
        batch = plate_list[i:i + batch_size]
        params_batch: Dict[str, Any] = {
            "resource_id": RESOURCE_ID_MILEAGE,
            "limit": 32000,
            "filters": json.dumps({"mispar_rechev": batch}, separators=(",", ":")),
        }
        try:
            resp = req.get(DATAGOV_URL, params=params_batch, timeout=120)
            resp.raise_for_status()
            data_batch: Dict[str, Any] = resp.json()
            batch_records: List[MileageRecord] = data_batch.get("result", {}).get("records", [])  # type: ignore[assignment]
            for rec in batch_records:
                plate = rec.get("mispar_rechev")
                if plate:
                    mileage_map[plate] = rec
        except Exception as e:  # broad catch keeps loop resilient
            print(f"Mileage batch fetch failed for plates[{i}:{i+batch_size}]: {e}")
    return mileage_map


def fetch_ownership_records(plate_list: List[str], batch_size: int = 100, session: Optional[requests.Session] = None) -> Dict[str, List[OwnershipRecord]]:
    """Fetch ownership history records (multiple ownerships per plate) using raw baalut_dt.

    Returns mapping: plate -> list of OwnershipRecord sorted by baalut_dt ascending (unknown last).
    """
    ownership_map: Dict[str, List[OwnershipRecord]] = {}
    if not plate_list:
        return ownership_map
    req = session or requests
    for i in range(0, len(plate_list), batch_size):
        batch = plate_list[i:i + batch_size]
        params_batch: Dict[str, Any] = {
            "resource_id": RESOURCE_ID_OWNERSHIP,
            "limit": 32000,
            "filters": json.dumps({"mispar_rechev": batch}, separators=(",", ":")),
        }
        try:
            resp = req.get(DATAGOV_URL, params=params_batch, timeout=120)
            resp.raise_for_status()
            data_batch: Dict[str, Any] = resp.json()
            batch_records: List[OwnershipRecord] = data_batch.get("result", {}).get("records", [])  # type: ignore[assignment]
            for rec in batch_records:
                plate_raw = rec.get("mispar_rechev")
                if plate_raw is None:
                    continue
                plate = str(plate_raw)
                ownership_map.setdefault(plate, []).append(rec)
        except Exception as e:
            print(f"Ownership batch fetch failed for plates[{i}:{i+batch_size}]: {e}")
    # sort each list by raw baalut_dt (numeric YYYYMMDD asc, unknown last)
    def sort_key(r: OwnershipRecord) -> tuple[str, float]:
        val = r.get("baalut_dt")
        if val is None:
            return ("99999999", r.get("rank", 0.0))
        s = str(val)
        digits = ''.join(ch for ch in s if ch.isdigit())
        if len(digits) == 8:
            return (digits, r.get("rank", 0.0))
        return ("99999999", r.get("rank", 0.0))
    for plate, lst in ownership_map.items():
        lst.sort(key=sort_key)
    return ownership_map


def parse_mileage(rec: Optional[MileageRecord]) -> Optional[int]:
    """Extract integer mileage from a MileageRecord; return None if missing/invalid."""
    if not rec:
        return None
    raw = rec.get("kilometer_test_aharon")
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip().replace(',', '')
        if not raw.isdigit():
            # try partial numeric prefix
            digits = ''.join(ch for ch in raw if ch.isdigit())
            raw = digits if digits.isdigit() else ''
    try:
        return int(raw)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def sort_records_by_mileage(records: List[VehicleRecord], mileage_map: Dict[str, MileageRecord], descending: bool = False) -> List[VehicleRecord]:
    """Return a new list of VehicleRecord sorted by mileage (missing mileage last)."""
    def key_func(v: VehicleRecord) -> tuple[int, int]:
        mileage = parse_mileage(mileage_map.get(v.get("mispar_rechev", "")))
        if mileage is None:
            # sentinel: always last regardless of order
            return (1, 0)
        # for ascending: (0, mileage), for descending: (0, -mileage)
        return (0, -mileage if descending else mileage)
    return sorted(records, key=key_func)


def print_statistics(records: List[VehicleRecord]) -> None:
    """Print ownership (baalut) statistics and month breakdown."""
    total = len(records)
    print(f"\nTotal vehicles: {total}")
    baalut_counter: Counter[str] = Counter(r.get("_baalut", "UNKNOWN") for r in records)

    # Build nested month counters per baalut
    baalut_month_counters: Dict[str, Counter[str]] = defaultdict(Counter)
    for r in records:
        baalut_month_counters[r.get("_baalut", "UNKNOWN")][r.get("_moed", "UNKNOWN")] += 1

    print("\nBaalut Statistics:")
    for baalut, count in baalut_counter.most_common():
        pct = (count / total * 100) if total else 0
        print(f"{baalut}: {count} vehicles ({pct:.2f}%)")

    print("\nBaalut -> moed_aliya_lakvish breakdown:")
    for baalut, count in baalut_counter.most_common():
        print(f"\n{baalut} (total {count}):")
        month_counter = baalut_month_counters[baalut]

        def month_sort_key(m: str) -> tuple[str, str]:
            if m == "UNKNOWN":
                return ("9999", "99")
            y, mth = m.split('-')
            return (y, mth)

        for month in sorted(month_counter.keys(), key=month_sort_key):
            m_count = month_counter[month]
            m_pct = (m_count / count * 100) if count else 0
            print(f"  {month}: {m_count} ({m_pct:.2f}%)")


def print_vehicle_mileage(records: List[VehicleRecord], mileage_map: Dict[str, MileageRecord], sort_by_mileage: bool = False, descending: bool = False) -> None:
    """Print combined vehicle and mileage information (optionally sorted by mileage)."""
    to_print: List[VehicleRecord] = sort_records_by_mileage(records, mileage_map, descending=descending) if sort_by_mileage else records
    order_desc = "descending" if descending else "ascending"
    if sort_by_mileage:
        print(f"\nVehicle + Mileage Records (sorted by mileage {order_desc}, missing last):")
    else:
        print("\nVehicle + Mileage Records:")
    for record in to_print:
        lp = record.get('mispar_rechev', '') or ''
        mileage_rec = mileage_map.get(lp)
        mileage_val = parse_mileage(mileage_rec)
        mileage_str = str(mileage_val) if mileage_val is not None else 'N/A'
        print(
            f"License Plate: {lp}, Year: {record.get('shnat_yitzur')}, Owner Type: {record.get('_baalut')}, "
            f"moed_aliya_lakvish: {record.get('moed_aliya_lakvish')}, mileage: {mileage_str}"
        )


def print_records_by_owner(records: List[VehicleRecord], owner_type: Optional[str] = None, mileage_map: Optional[Dict[str, MileageRecord]] = None, sort_by_mileage: bool = False, descending: bool = False) -> None:
    """Print records grouped by owner type (_baalut) or a single owner type.

    Args:
        records: Vehicle records list.
        owner_type: Specific owner type to display; if None, show all groups.
        mileage_map: Optional mileage records lookup.
        sort_by_mileage: If True, sort vehicles inside each owner group by mileage.
        descending: If sorting by mileage, choose descending order.
    """
    groups: Dict[str, List[VehicleRecord]] = defaultdict(list)
    for r in records:
        groups[r.get('_baalut', 'UNKNOWN')].append(r)

    if owner_type is not None:
        owner_key = owner_type if owner_type in groups else owner_type  # maintain key for message
        owner_records = groups.get(owner_type)
        print(f"\nRecords for owner type: {owner_key}")
        if not owner_records:
            print("  (no records found)")
            return
        if sort_by_mileage and mileage_map is not None:
            owner_records = sort_records_by_mileage(owner_records, mileage_map, descending=descending)
        else:
            owner_records.sort(key=lambda x: (
                x.get('_moed') if x.get('_moed') != 'UNKNOWN' else '9999-99',
                x.get('mispar_rechev', '') or ''
            ))
        for rec in owner_records:
            plate = rec.get('mispar_rechev', '') or ''
            mileage_val = parse_mileage(mileage_map.get(plate)) if mileage_map else None
            mileage_str = str(mileage_val) if mileage_val is not None else 'N/A'
            print(
                f"  Plate: {plate}, Year: {rec.get('shnat_yitzur')}, "
                f"moed: {rec.get('moed_aliya_lakvish')}, mileage: {mileage_str}"
            )
        return

    # All owner types
    ordered_owner_types = sorted(groups.keys(), key=lambda k: len(groups[k]), reverse=True)
    print("\nRecords grouped by owner type:")
    for owner in ordered_owner_types:
        owner_records = groups[owner]
        print(f"\nOwner Type: {owner} (count {len(owner_records)})")
        if sort_by_mileage and mileage_map is not None:
            owner_records = sort_records_by_mileage(owner_records, mileage_map, descending=descending)
        else:
            owner_records.sort(key=lambda x: (
                x.get('_moed') if x.get('_moed') != 'UNKNOWN' else '9999-99',
                x.get('mispar_rechev', '') or ''
            ))
        for rec in owner_records:
            plate = rec.get('mispar_rechev', '') or ''
            mileage_val = parse_mileage(mileage_map.get(plate)) if mileage_map else None
            mileage_str = str(mileage_val) if mileage_val is not None else 'N/A'
            print(
                f"  Plate: {plate}, Year: {rec.get('shnat_yitzur')}, "
                f"moed: {rec.get('moed_aliya_lakvish')}, mileage: {mileage_str}"
            )


def _format_baalut_dt(value: Any) -> str:
    """Format raw baalut_dt numeric (YYYYMM or YYYYMMDD) to MM-YYYY; return 'UNKNOWN' if invalid."""
    if value is None:
        return "UNKNOWN"
    s = str(value).strip()
    digits = ''.join(ch for ch in s if ch.isdigit())
    if len(digits) == 6:  # YYYYMM
        year = digits[0:4]
        month = digits[4:6]
    elif len(digits) == 8:  # YYYYMMDD -> use month/year only
        year = digits[0:4]
        month = digits[4:6]
    else:
        return "UNKNOWN"
    if not (month.isdigit() and year.isdigit()):
        return "UNKNOWN"
    try:
        m_i = int(month)
        if not (1 <= m_i <= 12):
            return "UNKNOWN"
    except ValueError:
        return "UNKNOWN"
    return f"{month}-{year}"


def print_ownership_summary(records: List[VehicleRecord], ownership_map: Dict[str, List[OwnershipRecord]], mileage_map: Dict[str, MileageRecord]) -> None:
    """Print ownership history summary per vehicle: count, latest ownership (MM-YYYY), mileage, moed_aliya_lakvish, mivchan_acharon_dt, grouped by last owner."""
    from collections import defaultdict
    owner_groups = defaultdict(list)
    for v in records:
        plate = v.get("mispar_rechev", "") or ""
        history = ownership_map.get(str(plate), [])
        count = len(history)
        latest: Optional[OwnershipRecord] = None
        for rec in reversed(history):
            val = rec.get("baalut_dt")
            if val is not None:
                digits = ''.join(ch for ch in str(val) if ch.isdigit())
                if len(digits) in (6, 8):
                    latest = rec
                    break
        if latest is None and history:
            latest = history[-1]
        latest_owner = latest.get("baalut") if latest else "N/A"
        latest_date_raw = latest.get("baalut_dt") if latest else "N/A"
        latest_date_fmt = _format_baalut_dt(latest_date_raw)
        mileage_val = parse_mileage(mileage_map.get(plate)) if mileage_map else None
        mileage_str = str(mileage_val) if mileage_val is not None else "N/A"
        moed_aliya_lakvish = v.get("moed_aliya_lakvish", "N/A")
        mivchan_acharon_dt = v.get("mivchan_acharon_dt", "N/A")
        owner_groups[latest_owner].append({
            "plate": plate,
            "count": count,
            "latest_date": latest_date_fmt,
            "mileage": mileage_str,
            "moed_aliya_lakvish": moed_aliya_lakvish,
            "mivchan_acharon_dt": mivchan_acharon_dt,
            "history": history
        })
    print("\nOwnership history summary (grouped by last owner):")
    for owner, vehicles in owner_groups.items():
        print(f"\nLast owner: {owner} ({len(vehicles)} vehicles)")
        for v in vehicles:
            print(f"  Plate: {v['plate']}, history entries: {v['count']}, latest date: {v['latest_date']}, mileage: {v['mileage']}, moed_aliya_lakvish: {v['moed_aliya_lakvish']}, mivchan_acharon_dt: {v['mivchan_acharon_dt']}")
            if v['history']:
                print("    Full ownership timeline:")
                for rec in v['history']:
                    raw_dt = rec.get("baalut_dt")
                    fmt_dt = _format_baalut_dt(raw_dt)
                    owner_rec = rec.get("baalut") or "UNKNOWN"
                    rank_val = rec.get("rank")
                    print(f"      {fmt_dt} -> {owner_rec}" + (f" (rank {rank_val})" if rank_val is not None else ""))
            else:
                print("    No ownership history records found.")


def main() -> None:
    year: str = "2022"
    kod_degem: str = "255"
    kod_tozar: str = "416"
    cached_session = requests_cache.CachedSession("mileage_http_cache", expire_after=3600)
    records: List[VehicleRecord] = fetch_vehicle_records(year=year, kod_degem=kod_degem, kod_tozar=kod_tozar, session=cached_session)
    print_statistics(records)
    plates: List[str] = [r.get("mispar_rechev", "") for r in records if r.get("mispar_rechev")]
    mileage_map: Dict[str, MileageRecord] = fetch_mileage_records(plates, session=cached_session)
    ownership_map: Dict[str, List[OwnershipRecord]] = fetch_ownership_records(plates, session=cached_session)
    # print_records_by_owner(records, owner_type="ליסינג", mileage_map=mileage_map, sort_by_mileage=True, descending=False)
    print_ownership_summary(records, ownership_map, mileage_map)


if __name__ == '__main__':
    main()