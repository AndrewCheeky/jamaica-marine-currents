"""Persist bank-history.json to a dedicated GitHub branch via the GitHub Contents API.

Usage: python history_storage.py restore|save
Requires GITHUB_TOKEN and GITHUB_REPOSITORY in GitHub Actions.
"""
import base64
import hashlib
import json
import os
import sys
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
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise RuntimeError(f'GitHub history request failed (HTTP {err.code})') from err


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
    previous=feature_content()
    payload={'message':'Update ocean feature history','branch':BRANCH,
             'content':base64.b64encode(raw).decode()}
    if previous:payload['sha']=previous['sha']
    result=request('PUT',f'/contents/{FEATURE_FILE}',payload)
    if not result or not result.get('content',{}).get('sha'):
        raise RuntimeError('Feature history save failed')
    verified=feature_content()
    if not verified or hashlib.sha256(base64.b64decode(verified['content'])).digest()!=hashlib.sha256(raw).digest():
        raise RuntimeError('Feature history checksum mismatch')
    print('FEATURE HISTORY VERIFY: SHA-256 matches')


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
    previous = get_content()
    payload = {
        'message': 'Update marine environmental observation history',
        'branch': BRANCH,
        'content': base64.b64encode(raw).decode(),
    }
    if previous:
        payload['sha'] = previous['sha']
    result=request('PUT', f'/contents/{FILE}', payload)
    if not result or not result.get('content',{}).get('sha'):
        raise RuntimeError('History save did not return a committed file')
    verified=get_content()
    if not verified or hashlib.sha256(base64.b64decode(verified['content'])).digest()!=hashlib.sha256(raw).digest():
        raise RuntimeError('History save verification failed: remote bytes differ')
    print('HISTORY VERIFY: saved history SHA-256 matches local archive')
    save_features()
    print(f'HISTORY SAVE: {len(banks)} banks; '
          f'{sum(len(v) for v in banks.values() if isinstance(v,list))} snapshots persisted')


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('restore','save'):
        sys.exit('Usage: python history_storage.py restore|save')
    {'restore': restore, 'save': save}[sys.argv[1]]()
