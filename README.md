# Jamaica Marine Currents — v3.8.5 starter

This project generates a **real Copernicus Marine** ocean surface-current map and publishes it using GitHub Pages. No map is published if forecast retrieval fails; fabricated maps are never substituted.

## Setup
1. Upload all files to `AndrewCheeky/jamaica-marine-currents`, preserving `.github/workflows`.
2. In repository Settings → Secrets and variables → Actions, create `COPERNICUSMARINE_SERVICE_USERNAME` and `COPERNICUSMARINE_SERVICE_PASSWORD` using your Copernicus account. Never commit credentials.
3. In Settings → Pages, select **GitHub Actions** as the source.
4. Run Actions → **Generate Jamaica currents map** → Run workflow.
5. Open the Pages deployment URL after a successful run. Confirm the data timestamp.
6. Replace `banks.json` with the actual 13 locations from your `banks` Google Sheet; only two known coordinates are included, and the remaining 11 are not guessed.

## Dataset
Default `cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i` under `GLOBAL_ANALYSISFORECAST_PHY_001_024`. **Verify that this exact dataset ID is available in your Copernicus catalog.** Change workflow `COPERNICUS_DATASET_ID` if needed. The program uses the closest available model timestamp to the selected Jamaica time, and labels that timestamp explicitly. A snapshot is not a six-hour average.

## Security / operations
GitHub Pages is public. This starter publishes only forecast maps and bank names/coordinates; do not upload subscriber information. First Cartopy run may download coastline data. Copernicus terms/attribution must be reviewed before commercial deployment. Not for navigation.

## Next stage
After first successful live map: verify all 13 banks, add Google Apps Script link and popup, and align scheduled generation with the model release cycle.

## Branding and marker update
The marker now uses `site/assets/fish-pin.png` with a cropped transparent background. The map and visible webpage do not prominently identify the data provider. Before public/commercial distribution, verify and satisfy applicable Copernicus Marine attribution requirements in an appropriate legal/credits location.

## v3.8.5 satellite-map refresh
- Fish-pin artwork is the user-supplied transparent PNG, rendered about 10 pixels wide (aspect ratio preserved).
- Jamaica land imagery uses Cartopy's georeferenced Natural Earth stock raster, rather than a plain white/solid land fill. It is lower resolution than commercial satellite tiles; true high-resolution satellite imagery requires a separate licensed imagery source.
- Current-speed shading uses the **real downloaded Copernicus grid**, not the illustrative AI mockup.
- Includes current-speed colourbar in knots, current-direction arrow key, north indicator, and approximate 100 km scale bar at latitude 16.35 N.
- Public-facing header omits provider branding; data provenance remains in forecast.json and README for transparency and licensing review.
- Only bank coordinates in banks.json appear. Populate all 13 verified banks before production.
- Run a **fresh** GitHub Actions workflow, not a rerun of the earlier successful run, to avoid duplicate github-pages artifacts.

## Latest update: 10 px icon + colour/arrow legend
- Uses the user's supplied transparent `site/assets/fish-pin.png` and scales it to fit **within 10×10 pixels** on the output map.
- Colour legend labels current speeds in knots (blue slower, yellow/red faster).
- White arrowheads point in the direction the current moves; vector magnitude scales with current speed.
- The existing georeferenced Natural Earth land raster is retained. It is a low-resolution Earth image, **not commercial high-resolution satellite imagery**. Higher-resolution satellite imagery requires a separately licensed raster tile source.
- The workflow is otherwise unchanged. **Start a new workflow run** rather than re-running an old run to avoid duplicate `github-pages` artifacts.
- The initial `banks.json` only contains two verified banks; replace it with all 13 before interpreting markers as complete.

## v3.8.5 white-land + 13 × 20 px fish pins (current revision)
- Jamaica and other land areas are **plain white**, masking ocean currents; no satellite imagery is used.
- `site/assets/fish-pin.png` is the supplied transparent fish-pin, resized to **13 × 20 px**.
- Each plotted bank marker is drawn at **13 × 20 output pixels** (not 10 × 10).
- The current-speed colourbar is in **knots**; white arrows indicate **the direction water moves toward**, with arrow length representing relative velocity.
- Bank names and positions still come only from `banks.json` (currently two verified examples, not all 13).
- To install: upload the contents to the repository root, overwriting `generate.py`, `README.md`, and `site/assets/fish-pin.png`. Keep `.github/workflows/currents.yml`. Then launch **a new workflow run**, not a rerun of the same run.
- Cartopy Natural Earth 10m land polygons require a first-run download. The map is a forecast visualization, **not for navigation**.

## Clean-map revision
- Website footer: **Copernicus Forecast Model**.
- Removed explanatory legend captions and extra footer text from generated PNG; retained the numeric current-speed colour scale, bank labels, model timestamp, north arrow, and distance scale.
- Jamaica land remains plain white. Marker artwork remains 13×20 pixels.

## v3.8.5 smooth-current rendering and in-map legend
- Interpolates the existing forecast current-speed grid 5x for display, then lightly blends cell boundaries while respecting missing values. This improves visual smoothness but **does not add real forecast detail or resolution**.
- Current speed colour scale (knots) and flow-arrow explanation are now inside the **lower-right corner of the actual map**, on a compact semi-transparent panel. They no longer occupy the black area outside the map.
- White land, the 13 × 20 px transparent fish-pin, forecast timestamps, and the Copernicus dataset retrieval remain unchanged.
- Requires SciPy (added to requirements.txt).
- Workflow unchanged. Start a **new** workflow_dispatch run instead of rerunning an old run to avoid duplicate github-pages artifacts.
