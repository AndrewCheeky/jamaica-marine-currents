#!/usr/bin/env python3
"""Install the visible workflow into GitHub's required workflow directory."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
source = root / "github-workflows" / "currents.yml"
target = root / ".github" / "workflows" / "currents.yml"
if not source.is_file():
    raise SystemExit("Missing github-workflows/currents.yml")
content = source.read_text(encoding="utf-8")
for required in ("contents: write", "Restore persistent history", "Save and verify persistent history", "Run regression tests"):
    if required not in content:
        raise SystemExit(f"Workflow validation failed: missing {required}")
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, target)
print(f"Installed GitHub Actions workflow: {target.relative_to(root)}")
print("Next: git add -A && git commit -m 'Deploy v3.8.42' && git push origin main")
