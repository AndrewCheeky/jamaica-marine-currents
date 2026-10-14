# v3.9.2 — Clickable GPS feature map

- Added a geographically positioned interactive Leaflet map for Ocean Fronts & Fishing Features, retaining All / SST Fronts / Currents / Eddies buttons.
- Existing numerical detections are exported as GeoJSON point markers and actual contour-derived lines. Selecting a line or point opens a popup.
- GPS in decimal degrees and degrees/decimal minutes; copy button; approximate search radius, strength, historical matching dates, model-valid timestamps and uncertainty notice.
- Selected fishing bank filters candidate point markers; environmental boundary lines remain visible for context.
- Existing static feature PNGs are still generated as artifacts, but the feature view uses the interactive map. Other map layers retain their existing image behaviour.
- Map tiles and Leaflet assets are loaded from public third-party servers in the browser; if unavailable, the existing bank feature summary remains readable. The interactive map is not suitable for navigation.
- No new Copernicus requests. Persistent history workflow and 730-day bank-history retention unchanged.
- No GPT integration or species-specific catch prediction in this release.
