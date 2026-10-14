# v3.9.0 — Ocean Fronts & Fishing Features

## Included
- New **Ocean Fronts & Fishing Features** overlay in the existing marine map dropdown.
- Numerical SST front gradients, current convergence, current shear, and *possible* rotation features calculated on georeferenced model grids.
- Native-grid derivatives in metric coordinates, coastal/missing-data exclusion, thresholded feature contours, and labelled map legend.
- Bank selector showing approximate candidate GPS centre points, realistic model-cell search radii, and distinct-date persistence observations.
- GeoJSON (`site/ocean-features.geojson`) plus bank summaries in `site/forecast.json`.
- 30-day feature-history archive, with matching-date persistence evaluated over the preceding seven calendar days, saved to existing `marine-observation-history` branch as **a separate file**. Original bank-history.json and its 730-day retention remain unchanged.
- No additional Copernicus API requests: analysis uses the same current-period SST and current grids already downloaded by `generate.py`.
- Six new numerical/persistence regression tests (28 total).

## Scientific limits
This is an **experimental environmental-feature detector**, not validated fishing hotspots. Rotation is inferred from vorticity magnitude and must not be described as a verified eddy. Current convergence from a coarse ocean model does not establish fish abundance. Candidate GPS points have uncertainty and are not navigation waypoints. Bank search areas are provisional 45-km radii centred on the existing bank coordinates, **not verified fishing-bank boundaries**. Actual marine model grid resolution limits precision. Repeated model-valid dates are not independent historical observations.

## Deployment
The ZIP includes `.github/workflows/currents.yml` and a visible workflow installer. If GitHub web upload omits hidden files, run `python3 install_workflow.py` once in Codespaces and commit the resulting workflow. The existing workflow already invokes history restore/save, which now also handles optional `feature-history.json` without modifying the established `bank-history.json`.

**Validation:** 28 unit tests passed and JavaScript syntax checked. Full live Copernicus execution and GitHub Pages rendering have not been verified here; GitHub Actions requires configured credentials and network access.
