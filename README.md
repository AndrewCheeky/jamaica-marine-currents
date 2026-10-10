# Jamaica Marine Weather — Ocean Currents v3.8.6

## New in this release
- Three **independently generated** model snapshots: **Current**, **Tomorrow** and **Weekend**. Each is selected from actual available Copernicus model timestamps; no relabeling of one image.
- Website forecast selector shows the exact model timestamp in **Jamaica local time**.
- Scheduled refreshes four times daily, at approximately **12:15 AM, 6:15 AM, 12:15 PM, 6:15 PM Jamaica time** (GitHub scheduled runs can be delayed).
- Maintains all 13 spreadsheet locations, fish-pin, white land, 5x blended display, and in-map speed scale.
- Existing `currents.png` retained as a compatibility alias for Tomorrow's forecast.

## Installation
1. Extract ZIP, upload the contents **including `.github/workflows/currents.yml`** to the root of `AndrewCheeky/jamaica-marine-currents` on the `main` branch.
2. Keep existing GitHub repository secrets `COPERNICUSMARINE_SERVICE_USERNAME` and `COPERNICUSMARINE_SERVICE_PASSWORD`.
3. Go to **Actions → Generate Jamaica currents maps → Run workflow**. Start a new run, not Re-run jobs on an older run.
4. Confirm all three `currents-*.png` images and `forecast.json` were generated and the Pages deployment succeeded.
5. Open `https://andrewcheeky.github.io/jamaica-marine-currents/` and test all three buttons; hard refresh if necessary.

## Model timing
- **Current**: model timestamp nearest the generation time (may be a few hours ahead or behind).
- **Tomorrow**: model timestamp nearest **12 noon Jamaica time tomorrow**.
- **Weekend**: model timestamp nearest **12 noon Jamaica time on the upcoming Saturday**; on Sunday, uses Sunday noon.
- If any target has no available model timestamp within 6 hours, the generation job **fails instead of publishing misleading data**. The last successful GitHub Pages deployment remains available.
- Copernicus data/model availability and GitHub schedule timing are outside this repository's control. Each forecast displays its actual model time.

## Deployment safety
- Does **not** change Google Apps Script or email delivery.
- Retains all existing `banks.json` coordinates and image assets.
- Pins are the original 13x20 pixel custom icon.
- Smoothing changes visualization only; it does not add model resolution.
- No new secrets or infrastructure required.
- The Node.js 20 GitHub Actions deprecation warning can be addressed by upgrading pinned actions separately; the workflow keeps the previously working action versions to reduce deployment risk.
