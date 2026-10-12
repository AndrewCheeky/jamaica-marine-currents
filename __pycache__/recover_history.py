"""Offline recovery: merge available old bank-history.json files into a backup copy.

Usage: python recover_history.py CURRENT.json OLD1.json [OLD2.json ...] --output MERGED.json
Does not fetch GitHub branches/artifacts or fabricate lost measurements.
"""
import argparse
import json
from pathlib import Path
from history_storage import validate_history


def merge(current, sources):
    result=json.loads(json.dumps(current))
    result.setdefault('banks',{})
    recovered=0
    for source in sources:
        for key, rows in source['banks'].items():
            target=result['banks'].setdefault(key,[])
            identities={(r.get('sst_date'),r.get('current_date'),r.get('chlorophyll_date'),r.get('score_model_version')) for r in target}
            for row in rows:
                identity=(row.get('sst_date'),row.get('current_date'),row.get('chlorophyll_date'),row.get('score_model_version'))
                if identity not in identities:
                    target.append(row.copy())
                    identities.add(identity)
                    recovered+=1
    return result,recovered


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('current',type=Path)
    parser.add_argument('old',type=Path,nargs='+')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    current=validate_history(args.current.read_bytes())
    sources=[validate_history(path.read_bytes()) for path in args.old]
    result,count=merge(current,sources)
    if args.output.resolve() in {path.resolve() for path in [args.current,*args.old]}:
        parser.error('Output must be a NEW file, never overwrite recovery sources')
    args.output.write_text(json.dumps(result,indent=2))
    print(f'RECOVERY: {count} unique observations added; original files unchanged')

if __name__=='__main__':main()
