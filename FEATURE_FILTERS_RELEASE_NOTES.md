# v3.9.1 — Clickable Ocean Feature Filters

The Ocean Fronts & Fishing Features dropdown now shows four clickable buttons directly above the map: **All**, **SST Fronts**, **Currents**, **Eddies**. Each selection displays its own generated map, and the selected bank's feature summary filters accordingly. Currents includes convergence and shear. The All view preserves the original combined map.

The same SST and current numerical grids are used; no additional Copernicus requests. Existing map layers and history storage are unchanged. Feature GPS candidate coordinates remain in the bank detail panel; map-marker popups are not implemented in this release.

Deploy by replacing files in the existing repository, commit to main, then run GitHub Actions. If the workflow is already installed, no install script is required.
