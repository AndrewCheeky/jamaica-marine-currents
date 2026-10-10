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
