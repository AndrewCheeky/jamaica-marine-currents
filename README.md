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
