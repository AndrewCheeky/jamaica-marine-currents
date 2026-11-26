"""Persist bank-history.json to a dedicated GitHub branch via the GitHub Contents API.

Usage: python history_storage.py restore|save
Requires GITHUB_TOKEN and GITHUB_REPOSITORY in GitHub Actions.
"""
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BRANCH = 'marine-observation-history'
FILE = 'bank-history.json'
LOCAL = Path('site/bank-history.json')
FEATURE_FILE = 'feature-history.json'
FEATURE_LOCAL = Path('site/feature-history.json')
API = f"https://api.github.com/repos/{os.environ.get('GITHUB_REPOSITORY', '')}"


def request(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
        'User-Agent': 'jamaica-marine-history',
    })
    # GitHub sometimes answers 5xx or drops the connection for a moment: wait and try again (3 tries).
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.load(res)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            if err.code in (500, 502, 503, 504) and attempt < 2:
                print(f'GitHub HTTP {err.code}; retrying in {10 * (attempt + 1)} s'); time.sleep(10 * (attempt + 1)); continue
            raise RuntimeError(f'GitHub history request failed (HTTP {err.code})') from err
        except (urllib.error.URLError, TimeoutError) as err:
            if attempt < 2:
                print(f'GitHub connection problem ({err}); retrying'); time.sleep(10 * (attempt + 1)); continue
            raise RuntimeError(f'GitHub history request failed ({err})') from err


def blob_sha(raw):
    """Git's own id for these exact bytes – what GitHub reports for the file it committed."""
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def put_verified(name, raw, message, current):
    """Commit raw to the history branch and confirm GitHub stored exactly these bytes.
    Checked against the commit's own file id, not by reading the file back straight away:
    GitHub's read-back can briefly return the previous copy, which made good saves look failed."""
    payload = {'message': message, 'branch': BRANCH, 'content': base64.b64encode(raw).decode()}
    if current: payload['sha'] = current['sha']
    result = request('PUT', f'/contents/{name}', payload)
    stored = (result or {}).get('content', {}).get('sha')
    if not stored:
        raise RuntimeError(f'{name}: save did not return a committed file')
    if stored != blob_sha(raw):
        raise RuntimeError(f'{name}: saved bytes differ from the local archive')
    return stored


def validate_history(raw):
    data=json.loads(raw)
    if not isinstance(data,dict) or not isinstance(data.get('banks'),dict):
        raise ValueError('History JSON missing banks dictionary')
    for key, rows in data['banks'].items():
        if not isinstance(key,str) or not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):
            raise ValueError('Invalid bank history records')
    return data


def get_content():
    return request('GET', f'/contents/{FILE}?ref={BRANCH}')


def feature_content():
    return request('GET', f'/contents/{FEATURE_FILE}?ref={BRANCH}')


def restore_features():
    item=feature_content()
    if item is None:
        print('FEATURE HISTORY RESTORE: first run; no previous feature history')
        return
    raw=base64.b64decode(item['content'])
    data=json.loads(raw)
    if not isinstance(data,dict) or not isinstance(data.get('banks'),dict):
        raise ValueError('Invalid feature history archive')
    FEATURE_LOCAL.parent.mkdir(parents=True,exist_ok=True)
    FEATURE_LOCAL.write_bytes(raw)
    print(f'FEATURE HISTORY RESTORE: {len(data["banks"])} banks')


def save_features():
    if not FEATURE_LOCAL.exists():
        print('FEATURE HISTORY SAVE: no new numerical features; prior archive preserved')
        return
    raw=FEATURE_LOCAL.read_bytes()
    data=json.loads(raw)
    if not isinstance(data,dict) or not isinstance(data.get('banks'),dict) or not data['banks']:
        raise ValueError('Refusing invalid/empty feature history')
    put_verified(FEATURE_FILE, raw, 'Update ocean feature history', feature_content())
    print('FEATURE HISTORY VERIFY: GitHub stored exactly the local bytes')


def restore():
    branch=request('GET', f'/git/ref/heads/{BRANCH}')
    if branch is None:
        print('HISTORY RESTORE: history branch does not exist; initial setup')
        return
    item = get_content()
    if not item:
        raise RuntimeError('History branch exists but bank-history.json is missing; refusing empty restore')
    raw = base64.b64decode(item['content'])
    data = validate_history(raw)
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    LOCAL.write_bytes(raw)
    restore_features()
    print(f'HISTORY RESTORE: {len(data["banks"])} banks; '
          f'{sum(len(v) for v in data["banks"].values() if isinstance(v,list))} snapshots')


def save():
    raw=LOCAL.read_bytes()
    data = validate_history(raw)
    banks = data.get('banks')
    if not isinstance(banks, dict) or not banks or not any(isinstance(v,list) and v for v in banks.values()):
        raise ValueError('Refusing to replace saved history with empty/invalid history')
    ref = request('GET', f'/git/ref/heads/{BRANCH}')
    if ref is None:
        default = request('GET', '')
        base = request('GET', f'/git/ref/heads/{default["default_branch"]}')
        request('POST', '/git/refs', {'ref': f'refs/heads/{BRANCH}', 'sha': base['object']['sha']})
        print('HISTORY SAVE: created persistent history branch')
    put_verified(FILE, raw, 'Update marine environmental observation history', get_content())
    print('HISTORY VERIFY: GitHub stored exactly the local archive')
    save_features()
    print(f'HISTORY SAVE: {len(banks)} banks; '
          f'{sum(len(v) for v in banks.values() if isinstance(v,list))} snapshots persisted')


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('restore','save'):
        sys.exit('Usage: python history_storage.py restore|save')
    {'restore': restore, 'save': save}[sys.argv[1]]()
