# v3.9.4 — Geographic alignment correction

- Replaced SVG image overlay with geographic coastline polygons rendered in Leaflet WGS84 coordinates, using the existing bundled generalized coastline geometry.
- Coastline and ocean-feature GeoJSON now share Leaflet projection and zoom/pan transforms.
- Set initial map bounds around Jamaica and its offshore banks, rather than a wide four-degree latitude viewport.
- Prevented map content overflow.
- Preserved feature filters, clickable GPS popups, feature-history persistence, existing data generation, and workflow.
- No third-party basemap tiles. Leaflet JavaScript/CSS still loads from CDN.
- Generalized coastline is for context only; not for navigation.
