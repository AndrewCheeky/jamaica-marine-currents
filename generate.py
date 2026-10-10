"""Generate a true surface-current map from Copernicus Marine gridded forecast."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib import patheffects as pe
from PIL import Image
import copernicusmarine

ROOT = Path(__file__).parent
OUT = ROOT / 'site'
OUT.mkdir(exist_ok=True)
TZ = ZoneInfo('America/Jamaica')
DATASET = os.environ.get('COPERNICUS_DATASET_ID', 'cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i')
USERNAME = os.environ['COPERNICUSMARINE_SERVICE_USERNAME']
PASSWORD = os.environ['COPERNICUSMARINE_SERVICE_PASSWORD']
# Geographic bounds must be checked against all banks when the complete list is supplied.
WEST, EAST, SOUTH, NORTH = -79.5, -74.5, 16.0, 20.0
now_local = datetime.now(TZ)
# Tomorrow noon is the initial static-map target; source time is displayed exactly.
target = (now_local + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
target_utc = target.astimezone(timezone.utc)

# Ask for a time interval around target; select closest returned time below.
ds = copernicusmarine.open_dataset(
    dataset_id=DATASET,
    variables=['uo', 'vo'],
    minimum_longitude=WEST, maximum_longitude=EAST,
    minimum_latitude=SOUTH, maximum_latitude=NORTH,
    start_datetime=(target_utc-timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M:%S'),
    end_datetime=(target_utc+timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M:%S'),
    minimum_depth=0, maximum_depth=1,
    username=USERNAME, password=PASSWORD,
)
if 'time' not in ds.coords or ds.sizes.get('time', 0) == 0:
    raise RuntimeError('Copernicus returned no model timestamps; no map published')
ds = ds.sel(time=np.datetime64(target_utc.replace(tzinfo=None)), method='nearest')
if 'depth' in ds.dims:
    ds = ds.isel(depth=0)
u = ds['uo'].squeeze(drop=True)
v = ds['vo'].squeeze(drop=True)
# Do not publish if data is missing or coordinates invalid.
lat_name = 'latitude' if 'latitude' in u.coords else 'lat'
lon_name = 'longitude' if 'longitude' in u.coords else 'lon'
lats = np.asarray(u[lat_name].values)
lons = np.asarray(u[lon_name].values)
uvals = np.asarray(u.values, dtype=float)
vvals = np.asarray(v.values, dtype=float)
if uvals.ndim != 2 or vvals.shape != uvals.shape or not np.isfinite(uvals).any():
    raise RuntimeError('Invalid current grid; no map published')
spd = np.hypot(uvals, vvals) * 1.943844  # m/s to knots
banks = json.loads((ROOT/'banks.json').read_text())
fig = plt.figure(figsize=(13.5, 9), dpi=145, facecolor='#061b33')
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([WEST, EAST, SOUTH, NORTH], crs=ccrs.PlateCarree())
# Intentionally no land imagery: Jamaica is white as requested.
max_speed = max(2.0, float(np.nanpercentile(spd, 99)))
mesh = ax.pcolormesh(lons, lats, spd, transform=ccrs.PlateCarree(),
                     cmap='turbo', shading='auto', vmin=0, vmax=max_speed,
                     alpha=.94, zorder=2)
# White land overlays the ocean current field; no satellite or terrain imagery.
ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='white', edgecolor='none', zorder=4)
ax.coastlines(resolution='10m', linewidth=.85, color='#27465e', zorder=5)
# Thin outline keeps the island identifiable even where forecast pixels
# overlap a coastline.
ax.add_feature(cfeature.BORDERS, linewidth=.3, edgecolor='#d8e9ef', zorder=4)
step = max(1, int(max(len(lons),len(lats))/28))
q = ax.quiver(lons[::step], lats[::step], uvals[::step,::step], vvals[::step,::step],
          transform=ccrs.PlateCarree(), color='white', alpha=.85,
          scale=12, width=.0022, headwidth=3.7, headlength=5.5, zorder=3)
# Vector arrows show direction of travel; arrow length is proportional to speed.
# Current speeds in colourbar are converted from m/s to knots.

# Supplied transparent fish-pin: exactly 13 x 20 output pixels at saved DPI.
icon_img = Image.open(ROOT/'site/assets/fish-pin.png').convert('RGBA').resize((13, 20), Image.Resampling.LANCZOS)
icon = np.asarray(icon_img)
for bank in banks:
    lat, lon = float(bank['lat']), float(bank['lon'])
    if not (SOUTH <= lat <= NORTH and WEST <= lon <= EAST):
        raise ValueError(f'Bank outside map bounds: {bank["name"]}')
    ab = AnnotationBbox(OffsetImage(icon, zoom=1.0), (lon, lat),
                        xycoords='data', frameon=False, pad=0, zorder=7)
    ax.add_artist(ab)
    label = ax.annotate(bank['name'], (lon, lat), xytext=(9, -7),
                        textcoords='offset points', fontsize=7.3,
                        color='white', fontweight='bold', zorder=8)
    label.set_path_effects([pe.withStroke(linewidth=2.5, foreground='#061b33')])

# True cartographic distance scale, evaluated at the chosen latitude.
# Longitude spacing in km at 17.5 degrees north is approx 111.32*cos(lat).
scale_lat = 16.35
scale_lon = -79.1
scale_km = 100
scale_dlon = scale_km / (111.32 * np.cos(np.deg2rad(scale_lat)))
ax.plot([scale_lon, scale_lon + scale_dlon], [scale_lat, scale_lat],
        color='white', lw=2.5, transform=ccrs.PlateCarree(), zorder=9)
for frac in [0, .5, 1]:
    x = scale_lon + frac * scale_dlon
    ax.plot([x, x], [scale_lat-.035, scale_lat+.035], color='white',
            lw=2, transform=ccrs.PlateCarree(), zorder=9)
    ax.text(x, scale_lat+.075, f'{int(scale_km*frac)}', color='white',
            fontsize=8, ha='center', transform=ccrs.PlateCarree(), zorder=9,
            path_effects=[pe.withStroke(linewidth=2, foreground='#061b33')])
ax.text(scale_lon + scale_dlon + .08, scale_lat+.075, 'km',
        color='white', fontsize=8, transform=ccrs.PlateCarree(), zorder=9)
ax.text(-74.9, 19.55, 'N ↑', color='white', fontsize=13, weight='bold',
        ha='center', transform=ccrs.PlateCarree(), zorder=9,
        path_effects=[pe.withStroke(linewidth=2, foreground='#061b33')])
source_time = np.datetime_as_string(ds['time'].values, unit='m') + ' UTC'
# Layout leaves room for a labelled legend and a source/licence footer.
ax.set_title('JAMAICA MARINE WEATHER  |  OCEAN CURRENTS FORECAST\n'
             + 'Model time: ' + source_time,
             fontsize=15, weight='bold', color='white', pad=17)
cb = fig.colorbar(mesh, ax=ax, orientation='horizontal', fraction=.048,
                  pad=.065, aspect=35, shrink=.78)
cb.set_label('CURRENT SPEED (knots) — blue: slower  |  yellow/red: faster', color='white', fontsize=11)
cb.ax.tick_params(labelcolor='white', colors='white')
cb.outline.set_edgecolor('white')
fig.text(.50, .073,
         'MAGENTA PIN  Fishing bank  |  WHITE ARROWS  Direction water moves toward (longer arrow = faster current)',
         color='white', ha='center', fontsize=9)
fig.text(.5, .035,
         'Forecast snapshot • Not for navigation • Data details and attribution: forecast.json / README',
         color='#c7d9eb', ha='center', fontsize=8)
fig.savefig(OUT/'currents.png', bbox_inches='tight', facecolor=fig.get_facecolor())
plt.close(fig)
metadata = {'dataset':DATASET,'model_time_utc':source_time,'generated_utc':datetime.now(timezone.utc).isoformat(),
            'target_jamaica':target.isoformat(),'bank_count':len(banks), 'data_provider':'Copernicus Marine', 'display_units':'knots', 'map_basemap':'Plain white land (Natural Earth coastline)', 'map_scale_km':100,'marker_pixels':{'width':13,'height':20},'arrow_meaning':'Direction water moves toward; magnitude proportional to speed'}
(OUT/'forecast.json').write_text(json.dumps(metadata, indent=2))
(OUT/'index.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jamaica Ocean Currents</title><style>body{font:16px Arial,sans-serif;background:#f4f8fc;color:#12253a;margin:0;padding:18px}main{max-width:1200px;margin:auto}img{width:100%;height:auto;border-radius:10px}small{color:#536879}</style></head><body><main><h1>Jamaica Marine Weather — Ocean Currents</h1><p>Tomorrow's model snapshot — see exact forecast timestamp on the map.</p><img src="currents.png" alt="Jamaica ocean surface-current forecast with fishing bank markers"><p><small>Forecast snapshot, not a six-hour average. Not for navigation.</small></p></main></body></html>''')
print('Generated:', metadata)
