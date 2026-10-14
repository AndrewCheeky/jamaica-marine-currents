# v3.8.44 — Selectable historical trend windows

- Adds 3-day, 7-day (default), and 30-day selectors to **How conditions are changing** for each bank.
- Uses distinct source dates for SST, surface current and chlorophyll; does not count repeated downloads as new observations.
- Windows use calendar dates anchored to the most recent available source date for the bank. Gaps remain gaps; no interpolation.
- With 1 observation, shows building history; with 2, a difference only; with 3–4, an early indication; with 5+, a descriptive comparison (not a fishing prediction).
- Shows source-date counts and latest values, and retains the small historical line charts.
- Preserves all forecast generation, existing scoring, 730-day history retention and GitHub workflow.
- Adds four regression tests, bringing the test suite to 21 tests.

## Deploy
Unzip and copy repository files to GitHub. In Codespaces:

```bash
python3 install_workflow.py
python3 -m unittest discover -s tests -v
git add -A
git commit -m "Deploy v3.8.44 selectable trend windows"
git push origin main
```

Run GitHub Actions and inspect the live website. Never delete `marine-observation-history`.
