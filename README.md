## v3.8.26 display cleanup

- Removed the Data completeness percentage column from the Fishing Opportunities species-score table. Completeness remains an internal scoring safeguard.
- Removed bank-selection instruction text from the Fishing Opportunities map image description.
- Retained the bank comparison, observation freshness and quality indicators, and historical trend charts.

# v3.8.19: Optional Bathymetric Contours

The Pelagic Fishing Intelligence map now has a checkbox to toggle a second image with generalized ocean-depth boundaries at 200, 500, 1,000 and 2,000 metres, where available. Source: **Natural Earth 1:10m bathymetry**, not GEBCO. The same already-fetched ocean data is used for both images, with no additional Copernicus API requests. Cartopy downloads Natural Earth shape files during the GitHub Action when not cached. If unavailable, the original pelagic map remains usable and the checkbox is disabled. Natural Earth polygons depict generalized depth zones, not high-resolution sounding lines. Not for navigation.

# Jamaica Marine Weather — v3.8.10 Local Marine Forecast

Based on the v3.8.8 multilayer GitHub Pages project. Includes a **Local Marine Forecast** section beneath the existing maps with two embedded Weatherproof.fi pages: the type=6 marine bulletin and the marine2.php animated wind forecast. **No Open Original Forecast links** are included. All existing map layers, controls, bank markers, build workflow and Copernicus configuration are retained.

## Deploy

1. Back up your current GitHub repository.
2. Upload the contents of this ZIP to the repository root, preserving existing repository secrets and variables.
3. Run the GitHub Actions map-generation workflow, or wait for its next scheduled run. The generated `site/index.html` will include the new section.
4. Check `https://maps.andrewcheeky.com/` on desktop and mobile.

## Important limitation

The forecast sources are displayed through cross-origin iframes. If Weatherproof.fi blocks framing using `X-Frame-Options` or Content-Security-Policy `frame-ancestors`, browsers will not display the embedded content. A static GitHub Pages website cannot override that restriction. Permission to embed/reuse the source content should be confirmed with its publisher, especially for commercial use. The website does not claim a local update timestamp for those external sources.

## v3.8.10 display text
The forecast section attributes content to Jamaica Met Office, uses concise panel descriptions, and ends with only “Not for navigation.” No source-opening links are included. Embedded source URLs remain unchanged.


## Sargassum / Possible Weedlines (v3.8.12)

The fourth map selection contains two USF Jamaica Floating Algae Density (FAD) views: daily and seven-day mean. The generator fetches the USF Jamaica image listing once per run and attempts to locate direct, dated FAD PNG/JPEG files. It validates the image bytes and extracts the observation dates from the published image filename. It does not calculate drift or invent detections.

**Important first-run check:** USF direct image links and automated reuse have not been independently verified from this build environment. On first GitHub Actions run, inspect the `USF FAD` log messages and the published `forecast.json` > `sargassum` > `views`. If no directly downloadable dated images are advertised, the site reports unavailable, rather than displaying invented satellite observations. Confirm USF permission for republication before using their images on a public site. Source: https://optics.marine.usf.edu/cgi-bin/optics_data?roi=JAMAICA&comp=1

The GitHub Actions cache stores the last validated satellite images and their metadata. It is best-effort, not permanent storage. The daily and seven-day products are updated independently. Dates are satellite observation dates, never workflow run dates.

Copernicus Marine credentials remain required for the existing current-map generator. If that API fails authentication, the current workflow will still fail before publishing, independently of USF imagery.

## v3.8.12 repair

The previous release incorrectly treated Sargassum as a forecast layer. The page now reads the dedicated USF FAD metadata and shows 1DAY / 7DAY controls, dates, and images independently. Current/Tomorrow/Weekend buttons are hidden for this observational layer. If USF imagery cannot be retrieved, the satellite image is hidden and a clear unavailable notice is displayed, rather than leaving the ocean-current map visible under the Sargassum label. This repairs the display integration but does **not** establish that USF offers machine-downloadable image files; inspect Actions logs for successful downloads.

## v3.8.13 interface adjustment

Sargassum now defaults to FAD 7DAY MEAN. Current / Tomorrow / Weekend controls are fully hidden while Sargassum is selected, including when the global navigation flex style is active. They remain available for ocean currents, SST and waves. The HTML template in generate.py is updated so changes persist on each build.

## v3.8.14: Chlorophyll-a (Copernicus Marine)

Enabled **Chlorophyll-a · Copernicus** in the map dropdown. This is a satellite-derived **observation**, not a forecast, so the Current/Tomorrow/Weekend buttons are hidden for this layer. The actual observation date is shown on the map and above it. The daily, gap-free 4 km L4 multi-sensor plankton dataset is `cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D` (product `OCEANCOLOUR_GLO_BGC_L4_NRT_009_102`). Units are mg/m³. Source: https://data.marine.copernicus.eu/product/OCEANCOLOUR_GLO_BGC_L4_NRT_009_102/services

The generator requests only Jamaica's bounding box and a recent rolling observation window. On retrieval failure, it retains the last verified image and date if available via Actions cache, or displays an unavailable notice. No invented values. Inspect GitHub Actions output for `Copernicus chlorophyll-a:`. Credentials already used by the existing Copernicus maps are reused. The new data retrieval was not tested against live Copernicus credentials in this build environment.

## v3.8.15 Chlorophyll-a Fishing Composite
The active Chlorophyll-a dropdown now displays a **single composite image**:
- Satellite-derived gap-filled daily chlorophyll-a (mg/m³) as the colour background.
- White contours of the strongest spatial gradients in smoothed log10 chlorophyll, calculated per kilometre from the observed grid. These are potential ocean fronts, **not fish predictions**.
- Optional dashed magenta contours for higher relative zooplankton carbon biomass from a Copernicus model, when available.
- Existing fishing-bank markers and independent satellite/model validity dates.

Environment variables `COPERNICUS_ZOO_DATASET_ID` and `COPERNICUS_ZOO_VARIABLE` can override the tentative defaults (`cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m`, `zooc`). Confirm these against the accessible Copernicus catalogue and the dataset's actual variables. The zooplankton product may be unavailable, renamed, or have different units. The renderer deliberately avoids asserting units for this optional field until confirmed. If zooplankton retrieval fails, chlorophyll and its gradients still render, and the UI explicitly says zooplankton is unavailable. No phytoplankton functional-type layer is included: it would require a separately verified source and interpretation.

**Validation:** Python compilation and archive integrity tested locally; live Copernicus credentials and data access not available in this environment. Do not interpret the illustrative mockup from the chat as measured data. No synthetic data is used in the generator.


## v3.8.16 Pelagic Fishing Intelligence Map
The former Chlorophyll-a Fishing Composite dropdown entry is now **Pelagic Fishing Intelligence Map · Copernicus**. It is a single generated PNG, not an additional browser-side map engine.

- Satellite-derived chlorophyll-a is the background. Strong, coherent chlorophyll-gradient areas are outlined in white. Coastal and isolated artifacts are suppressed.
- Orange outlines show stronger surface-temperature fronts from the existing Copernicus temperature model, when data is available and within four calendar days of the chlorophyll observation.
- Cyan dashed outlines indicate potential surface-current convergence inferred from negative horizontal divergence of Copernicus model surface velocities. This is a proxy, not an observed aggregation of baitfish.
- Small gold rings identify locations where the strongest chlorophyll and SST fronts are within approximately 13 km. These are overlaps of **environmental indicators**, not scored fishing hotspots.
- Magenta contours remain optional for zooplankton. The dataset identifier/variable remain tentative and must be validated independently.
- All optional layers fail independently. A missing SST, currents, or zooplankton dataset is omitted, not fabricated. Separate dates and availability flags are recorded in `site/chlorophyll.json` and `site/forecast.json`.
- The original 13 bank markers, marine maps, USF FAD, Met Office embeds, and non-navigation disclaimer remain.

**Deployment check:** After running GitHub Actions, inspect `forecast.json` -> `chlorophyll` for `sst_status`, `convergence_status`, `zooplankton_status`, and their dates. Look for `WARNING: pelagic` and `WARNING: optional zooplankton` in the logs. The new extra requests may increase run time and Copernicus quota usage. No live credentials or marine data were available for end-to-end verification in this build environment.


## v3.8.17 Pelagic map improvements
- Correct Copernicus daily zooplankton dataset: `cmems_mod_glo_bgc-plankton_anfc_0.25deg_P1D-m`, variable `zooc` (mmol/m³).
- Separate source observation dates; optional zooplankton omitted if more than 10 days apart from chlorophyll observation.
- Fewer chlorophyll-front artefacts near land, clearer in-map legend, labelled SST isotherms (°C), and interpretation note.
- GitHub repository variable `COPERNICUS_ZOO_DATASET_ID`, if explicitly configured, overrides the workflow default. Remove or update an old repository variable to use the correct dataset.
- No live Copernicus test performed in the build environment.


## v3.8.18 Separate Persistent Weedlines view
- Adds **Persistent Weedlines · 7-day USF indicator** as a distinct marine overlay option.
- Reuses the existing published USF FAD 7DAY MEAN image and dated metadata; **no extra satellite requests or synthetic values**.
- Hides forecast buttons for this observation-only view, and shows an explicit interpretation panel.
- **Important:** 7DAY MEAN is a *proxy* for sustained floating-algae presence, **not** a count of detected days. No red/orange/yellow day-count classifications are made. Computing verified multi-day detections requires a series of individual georeferenced daily observations, coverage masks and drift-aware matching, which are not supplied by the current FAD image downloader.
- All existing marine forecasts, Pelagic Intelligence, Sargassum FAD 1DAY/7DAY, and Met Office panels remain unchanged.
- Validation: local syntax, embedded HTML/JS structural checks, and ZIP integrity. Live USF refresh must be checked in GitHub Actions.

## v3.8.20 Fishing Opportunities and Ocean Eddies

Based on the user-selected v3.8.19 package (200, 500, 1000, 2000 m bathymetry; no 100 m contour).

- **Fishing Opportunities**: separate dropdown map showing SST, surface currents and fishing-bank markers. Select fishing style and one of the 13 banks for approximate SST/current conditions, a local thermal-gradient indicator, potential species groups, and clear limitations. Reuses numerical grids from the existing Current forecast generation, so it does not add a Copernicus request for this feature. It does **not** claim species suitability scores, catch likelihood, verified habitat, or live weedlines at a bank.
- **Ocean Eddies**: separate optional satellite sea-level anomaly and geostrophic-current map. Default Copernicus dataset `cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D`, variables `sla`, `ugos`, `vgos`. May be overridden using the GitHub repository variable `COPERNICUS_EDDY_DATASET_ID`. It shows eddy **context**, not validated individual eddy centres or boundaries. If unavailable, the other maps still publish.
- Maps are observational/planning aids, **not for navigation**. The existing Pelagic Intelligence map and bathymetry toggle remain unchanged.

Deployment: upload the ZIP contents to the repository root, preserving `.github/workflows/currents.yml`, commit, and run the workflow. Confirm the GitHub log includes generation of currents/SST and that `forecast.json` contains `fishing_opportunities` and `ocean_eddies`.

## v3.8.21 Fishing Opportunities assessment

- Based on v3.8.20, which itself retained the **v3.8.19** generalized 200/500/1,000/2,000 m bathymetric toggle. No 100 m contours have been added.
- Adds `opportunity_scoring.py` and a regional `jamaica.nc` GEBCO 2026 grid for **numeric depth assessment only**. The bathymetry overlay on the Pelagic map is unchanged.
- Fetches the latest available chlorophyll-a numerical grid separately for fishing-bank assessments. This adds an optional Copernicus read. If it fails, scores are calculated only when enough of the other inputs are available; missing data are not counted as zero.
- Displays a bank-level overall 0–100 index (the highest available species-group score, **not an average**) and separate species-group indices filtered by fishing method, with data completeness for each group.
- Inputs: SST, local thermal gradient, chlorophyll-a mg/m³, local chlorophyll gradient, surface current knots, GEBCO seabed depth. These are broad heuristic environmental indicators, **not calibrated habitat models or actual catch likelihood**. Weights and species response thresholds are provisional. Weedline and eddy observations are not yet quantitatively assessed, and seabed substrate, protected areas and regulations are not assessed.
- Each index requires at least 60% of its weighted inputs to be available. Missing factors are excluded from the denominator; scores with poor coverage are suppressed.
- GEBCO depths are approximate, not navigation soundings. The depth sampled is a nearby grid-cell neighbourhood median, not a verified fishing-bank sounding.
- This release has not been tested against live Copernicus data or rendered in GitHub Actions. Verify after deployment.


## v3.8.22: Multi-method species opportunity indices

- Adds **grouper** and **king / Spanish mackerel** groups. Mackerel is a broad grouping, not a verified species identification at any bank.
- Allows one species group under multiple methods with independently weighted profiles: tuna, wahoo, snapper, jacks, grouper and mackerel have multiple method profiles.
- Each species/method pairing is independently scored with its own data-completeness percentage. Existing map filter now shows all profiles for the selected method.
- Overall and per-method indices remain the highest available supported score, not catch probabilities or averaged species catch rates.
- Adds the requested footer to the generated website.
- The six indicators do **not** measure substrate, reef structure, baitfish, regulations, subsurface temperatures or verified species presence. Grouper habitat and mackerel species distinctions are therefore particularly uncertain. Do not treat scores as a recommendation to fish protected or closed species.
- This release was syntax-checked and subjected to offline sample scoring tests only; live data and GitHub Actions deployment remain unverified.

### v3.8.23 display adjustment
Fishing Opportunities bank details show observation **dates only** for chlorophyll-a, currents and SST. Underlying timestamp metadata is preserved for model integrity; other map forecast times are unchanged.


## v3.8.24 display refinements
- Fishing Opportunities image no longer instructs users to select a bank below the map.
- Fishing Intelligence menu label omits the provider name.
- Fishing Intelligence retrieval/observation metadata is centred above its map.
- Currents, SST and wave model times are rendered in Jamaica local time (UTC−5 year-round), with a clear gap between time and date. Metadata is also formatted in local time.
- Ocean Eddies embedded observation date is labelled as a Jamaica-local date; date-only satellite observations elsewhere are unchanged.
- Animated wind forecast iframe has a dark border matching the maps.
- Existing scoring, fishing banks and website footer are retained.


## v3.8.25: bank comparisons, freshness and history
- Fishing Opportunities includes a side-by-side table of all configured banks, ranked by selected fishing method, with one-click bank details. Scores remain experimental suitability indices, never catch probabilities.
- Per-bank model reference dates, satellite observation freshness and core-input availability are displayed. The chlorophyll freshness caution is triggered after 4 days, model reference date caution after 2 days; these are user-interface heuristics, not quality certification.
- Daily numerical SST, chlorophyll and surface-current snapshots accumulate in `site/bank-history.json`, restored across scheduled workflow runs using GitHub Actions cache. First deployment starts with little/no history. Trends only appear with 2+ distinct source dates.
- Historical snapshots are limited to a rolling 45-day retention and 90 source-date combinations per bank. This is not a backfilled historical dataset. GitHub Actions cache can be evicted or expire; for production-grade durable retention, move history to persistent object storage or a database.
- All pre-existing maps and site footer are retained.
