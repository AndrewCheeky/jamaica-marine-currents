# Jamaica Marine Weather — v3.8.8 multi-layer overlays

Adds a dropdown to the existing Copernicus GitHub Pages map: **Ocean Currents**, **Sea Surface Temperature**, and **Wave Height & Direction**. Current / Tomorrow / Weekend remain available, along with all 13 fishing-bank markers, white land, Jamaica local model timestamps, last-updated footer, and the existing ocean-current image paths. Phases 2 and 3 are displayed as disabled future choices.

## Deployment

1. Back up the working v3.8.7 GitHub repository.
2. Upload the **contents** of this ZIP to the repository root, replacing existing matching files (including `.github/workflows/currents.yml`). Keep existing repository secrets `COPERNICUSMARINE_SERVICE_USERNAME` and `COPERNICUSMARINE_SERVICE_PASSWORD`.
3. In GitHub Actions, run **Generate Jamaica marine overlay maps** using **Run workflow**. Review logs and the published Pages URL.
4. If SST or wave layers report unavailable, check the Copernicus Marine catalogue for your account's correct available forecast dataset IDs and variable names. Configure repository **Variables** `COPERNICUS_SST_DATASET_ID` and `COPERNICUS_WAVES_DATASET_ID` as needed. Default IDs are provisional and have not been live verified.
5. The existing Apps Script popup still opens the same GitHub Pages URL; no Apps Script changes are needed.

## Operational notes

- Scheduled builds remain four per day at 00:15, 06:15, 12:15 and 18:15 Jamaica time.
- SST uses `thetao` in °C. Wave significant height uses `VHM0` in metres; `VMDR` is the direction waves come **from**, converted to direction of travel for arrows.
- Current overlay remains mandatory. Optional layers fail gracefully (marked unavailable), without publishing misleading substitute maps.
- SST model time tolerance is 18h due to daily sampling; other overlays use 6h. All map panels show actual model timestamps.
- Data interpolation is **visual smoothing only**, not higher-resolution ocean data. Not for navigation.
- GitHub Pages has no built-in staging: for a no-downtime test, use a separate branch/repository or run `python generate.py` with valid credentials before replacing production.
