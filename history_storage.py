"""Persist bank-history.json to a dedicated GitHub branch via the GitHub Contents API.

Usage: python history_storage.py restore|save
Requires GITHUB_TOKEN and GITHUB_REPOSITORY in GitHub Actions.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BRANCH = 'marine-observation-history'
FILE = 'bank-history.json'
LOCAL = Path('site/bank-history.json')
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


def get_content():
    return request('GET', f'/contents/{FILE}?ref={BRANCH}')


def restore():
    item = get_content()
    if not item:
        print('HISTORY RESTORE: no saved branch/file; starting new history')
        return
    raw = base64.b64decode(item['content'])
    data = json.loads(raw)
    if not isinstance(data.get('banks'), dict):
        raise ValueError('Saved history has no valid banks object')
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    LOCAL.write_bytes(raw)
    print(f'HISTORY RESTORE: {len(data["banks"])} banks; '
          f'{sum(len(v) for v in data["banks"].values() if isinstance(v,list))} snapshots')


def save():
    data = json.loads(LOCAL.read_text())
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
        'content': base64.b64encode(LOCAL.read_bytes()).decode(),
    }
    if previous:
        payload['sha'] = previous['sha']
    request('PUT', f'/contents/{FILE}', payload)
    print(f'HISTORY SAVE: {len(banks)} banks; '
          f'{sum(len(v) for v in banks.values() if isinstance(v,list))} snapshots persisted')


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('restore','save'):
        sys.exit('Usage: python history_storage.py restore|save')
    {'restore': restore, 'save': save}[sys.argv[1]]()
