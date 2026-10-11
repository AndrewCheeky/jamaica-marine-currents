"""Maintain a compact observation-date-indexed history in the GitHub Actions cache.
This is an accumulating history from deployment, not a retrospective archive.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

FIELDS=('sst_c','chlorophyll_mg_m3','current_knots')
def update(path,banks,days=45):
    path=Path(path)
    try: old=json.loads(path.read_text()) if path.exists() else {}
    except (ValueError,OSError):old={}
    store=old.get('banks',{}) if isinstance(old.get('banks',{}),dict) else {}
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).date().isoformat()
    for bank in banks:
        key=bank['key'];rows=store.get(key,[])
        if not isinstance(rows,list):rows=[]
        row={'sst_date':str(bank.get('sst_time_utc') or '')[:10],
             'current_date':str(bank.get('current_time_utc') or '')[:10],
             'chlorophyll_date':str(bank.get('chlorophyll_date') or '')[:10]}
        row.update({f:bank.get(f) for f in FIELDS})
        # One snapshot per distinct combination of source dates. A model timestamp
        # alone is not a new measured satellite observation.
        identity=lambda x:(x.get('sst_date'),x.get('current_date'),x.get('chlorophyll_date'))
        if any(row[f] is not None for f in FIELDS) and any(row.values()):
            previous=next((r for r in rows if identity(r)==identity(row)),None)
            if previous:
                for f in FIELDS:
                    if previous.get(f) is None and row[f] is not None:previous[f]=row[f]
            else:rows.append(row)
        rows=[r for r in rows if max((r.get('sst_date') or '',r.get('current_date') or '',r.get('chlorophyll_date') or ''))>=cutoff]
        store[key]=sorted(rows,key=lambda r:(r.get('sst_date') or '',r.get('current_date') or '',r.get('chlorophyll_date') or ''))[-90:]
    result={'status':'available','retention_days':days,'banks':store}
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2))
    return result
