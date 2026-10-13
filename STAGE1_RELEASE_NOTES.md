# Jamaica Fishing Intelligence v3.8.43 — Stage 1 display refresh

Built from the v3.8.42 complete visible-files baseline.

## Display-only changes
- Renamed **Data freshness & quality** to **Ocean Conditions**.
- Shows concise temperature, surface-current and chlorophyll readings, with clear forecast-valid vs satellite-observed dates.
- Replaces raw freshness codes with an understandable chlorophyll freshness notice.
- Provides expandable **Data details** for technical metadata.
- Renamed **Historical conditions** to **How conditions are changing**.
- Shows readable recorded changes, retains mini-charts, and uses **More observations needed** when history is insufficient.
- Added **What this means for fishing** explanatory text without suggesting that short histories predict catch rates.
- Added expandable **About this history** context.

## Preserved
- Bank comparisons and experimental opportunity scores
- Marine API and image collection, caching and source logic
- Persistent history restoration, saving, verification and 730-day retention
- GitHub Actions workflow and installation mechanism

## Installation
The ZIP intentionally contains visible files only. In GitHub Codespaces extract/upload its files into the repository root, then run:

```bash
python3 install_workflow.py
python3 -m unittest discover -s tests -v
git add -A
git commit -m "Jamaica Fishing Intelligence v3.8.43 stage 1 display"
git push origin main
```

Use GitHub Actions to run the workflow and verify the generated website. Do not delete the `marine-observation-history` branch.
