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
from scipy.ndimage import zoom, gaussian_filter
from matplotlib.patches import FancyBboxPatch
import copernicusmarine

ROOT = Path(__file__).parent
OUT = ROOT / 'site'
OUT.mkdir(exist_ok=True)
TZ = ZoneInfo('America/Jamaica')
DATASET = os.environ.get('COPERNICUS_DATASET_ID', 'cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i')
# Override IDs in GitHub repository variables if Copernicus changes product IDs.
SST_DATASET = os.environ.get('COPERNICUS_SST_DATASET_ID', 'cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m')
WAVES_DATASET = os.environ.get('COPERNICUS_WAVES_DATASET_ID', 'cmems_mod_glo_wav_anfc_0.083deg_PT3H-i')
USERNAME = os.environ['COPERNICUSMARINE_SERVICE_USERNAME']
PASSWORD = os.environ['COPERNICUSMARINE_SERVICE_PASSWORD']
# Geographic bounds must be checked against all banks when the complete list is supplied.
WEST, EAST, SOUTH, NORTH = -79.5, -74.5, 16.0, 20.0
import shutil

PAGE = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jamaica Marine Weather | Ocean Overlays</title><style>:root{color-scheme:light}*{box-sizing:border-box}body{font:16px system-ui,Arial,sans-serif;background:#f4f8fc;color:#12253a;margin:0;padding:16px}main{max-width:1200px;margin:auto}h1{font-size:clamp(1.3rem,3vw,2rem);margin:8px 0 14px}nav{display:flex;flex-wrap:wrap;gap:9px;margin:0 0 12px}button,select{border:1px solid #aec4d6;background:white;color:#163553;border-radius:8px;padding:11px 14px;font:inherit;cursor:pointer}button[aria-pressed="true"]{background:#123c63;color:white;border-color:#123c63}select{min-width:260px;max-width:100%}label{display:block;margin-bottom:6px;font-weight:650}img{display:block;width:100%;height:auto;border-radius:10px;background:#061b33}#time{margin:8px 0 12px;color:#344c65;font-weight:600}small{color:#536879}p{line-height:1.45}.controls{margin:0 0 14px}.notice{color:#a44900}#map[aria-busy="true"]{opacity:.55}</style></head><body><main><h1>Jamaica Marine Weather — Ocean Overlays</h1><div class="controls"><label for="layer">Choose marine overlay</label><select id="layer"><option value="currents">Ocean Currents · Existing</option><option value="sst">Sea Surface Temperature · Phase 1</option><option value="waves">Wave Height &amp; Direction · Phase 1</option><option disabled>──────── Future overlays ────────</option><option disabled>Chlorophyll-a · Phase 2</option><option disabled>Swell Period · Phase 2</option><option disabled>Subsurface Currents · Phase 3</option><option disabled>Salinity · Phase 3</option><option disabled>Ocean Fronts · Phase 3</option></select></div><nav aria-label="Forecast period"><button type="button" data-period="current" aria-pressed="true">Current</button><button type="button" data-period="tomorrow" aria-pressed="false">Tomorrow</button><button type="button" data-period="weekend" aria-pressed="false">Weekend</button></nav><p id="time" aria-live="polite">Loading forecast metadata…</p><img id="map" src="currents-current.png" alt="Current ocean currents forecast for Jamaica with 13 location markers"><p id="message" class="notice" role="status"></p><p><small>Copernicus Marine forecast models · Model timestamps shown for each forecast · <span id="updated">Last updated: loading…</span> · Not for navigation.</small></p></main><script>(async()=>{const status=document.querySelector(\'#time\'),map=document.querySelector(\'#map\'),layer=document.querySelector(\'#layer\'),msg=document.querySelector(\'#message\');let data;try{const r=await fetch(\'forecast.json\',{cache:\'no-store\'});if(!r.ok)throw Error(\'Metadata unavailable\');data=await r.json();const updated=document.querySelector(\'#updated\');if(data.generated_utc){const d=new Date(data.generated_utc);updated.textContent=\'Last updated: \'+new Intl.DateTimeFormat(\'en-JM\',{timeZone:\'America/Jamaica\',weekday:\'short\',day:\'2-digit\',month:\'short\',year:\'numeric\',hour:\'2-digit\',minute:\'2-digit\',hour12:true}).format(d)+\' (Jamaica time)\';}else updated.textContent=\'Last updated: unavailable\';let period=\'current\';function show(){const key=layer.value;const item=(data.layers||{})[key];const f=item?.forecasts?.find(x=>x.key===period);document.querySelectorAll(\'button[data-period]\').forEach(b=>b.setAttribute(\'aria-pressed\',String(b.dataset.period===period)));if(!f){status.textContent=\'This overlay is currently unavailable.\';msg.textContent=item?.error||\'Try a different overlay.\';return;}msg.textContent=\'\';status.textContent=f.label+\' · \'+item.label+\' · Model time: \'+f.model_time_jamaica;map.setAttribute(\'aria-busy\',\'true\');const next=new Image();next.onload=()=>{map.src=next.src;map.alt=f.label+\' \'+item.label+\' map of Jamaica\';map.removeAttribute(\'aria-busy\')};next.onerror=()=>{map.removeAttribute(\'aria-busy\');msg.textContent=\'Map image unavailable. Showing previous map.\'};next.src=f.image;}layer.addEventListener(\'change\',show);document.querySelectorAll(\'button[data-period]\').forEach(b=>b.addEventListener(\'click\',()=>{period=b.dataset.period;show()}));show();}catch(e){status.textContent=\'Forecast metadata unavailable; displaying last published current map.\';document.querySelector(\'#updated\').textContent=\'Last updated: unavailable\';msg.textContent=\'\';}})();</script></body></html>'
now_local = datetime.now(TZ)

def next_weekend_noon(now):
    # Upcoming Saturday, or today's Saturday; on Sunday use Sunday noon.
    if now.weekday() == 6:
        day = now.date()
    else:
        day = (now + timedelta(days=(5-now.weekday()) % 7)).date()
    return datetime(day.year, day.month, day.day, 12, tzinfo=TZ)

def forecast_targets(now):
    return {
        'current': now,
        'tomorrow': (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0),
        'weekend': next_weekend_noon(now),
    }

banks = json.loads((ROOT/'banks.json').read_text())

def generate_one(key, target, layer="currents"):
    target_utc = target.astimezone(timezone.utc)
    config = {
        'currents': (DATASET, ['uo', 'vo']),
        'sst': (SST_DATASET, ['thetao']),
        'waves': (WAVES_DATASET, ['VHM0', 'VMDR']),
    }
    dataset_id, variables = config[layer]
    opts = dict(minimum_depth=0, maximum_depth=1) if layer in ('currents', 'sst') else {}
    ds = copernicusmarine.open_dataset(
        dataset_id=dataset_id,
        variables=variables,
        minimum_longitude=WEST, maximum_longitude=EAST,
        minimum_latitude=SOUTH, maximum_latitude=NORTH,
        start_datetime=(target_utc-timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M:%S'),
        end_datetime=(target_utc+timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M:%S'),
        username=USERNAME, password=PASSWORD, **opts,
    )
    if 'time' not in ds.coords or ds.sizes.get('time', 0) == 0:
        raise RuntimeError('Copernicus returned no model timestamps; no map published')
    ds = ds.sel(time=np.datetime64(target_utc.replace(tzinfo=None)), method='nearest')
    actual_utc = datetime.fromisoformat(np.datetime_as_string(ds['time'].values, unit='s') + '+00:00')
    if abs((actual_utc - target_utc).total_seconds()) > (18 if layer == 'sst' else 6) * 3600:
        raise RuntimeError(f'{layer}/{key}: model time too far from requested target')
    if 'depth' in ds.dims:
        ds = ds.isel(depth=0)
    scalar_var = {'currents': 'uo', 'sst': 'thetao', 'waves': 'VHM0'}[layer]
    scalar = ds[scalar_var].squeeze(drop=True)
    lat_name = 'latitude' if 'latitude' in scalar.coords else 'lat'
    lon_name = 'longitude' if 'longitude' in scalar.coords else 'lon'
    lats = np.asarray(scalar[lat_name].values)
    lons = np.asarray(scalar[lon_name].values)
    if layer == 'currents':
        uvals = np.asarray(ds['uo'].squeeze(drop=True).values, dtype=float)
        vvals = np.asarray(ds['vo'].squeeze(drop=True).values, dtype=float)
        spd = np.hypot(uvals, vvals) * 1.943844
    elif layer == 'sst':
        spd = np.asarray(scalar.values, dtype=float)
        # Copernicus thetao is in degrees Celsius; do not offset Kelvin.
    else:
        spd = np.asarray(scalar.values, dtype=float)
        wave_dir = np.asarray(ds['VMDR'].squeeze(drop=True).values, dtype=float)
    if spd.ndim != 2 or spd.shape != (len(lats), len(lons)) or not np.isfinite(spd).any():
        raise RuntimeError(f'{layer}: invalid ocean grid; no map published')
    fig = plt.figure(figsize=(13.5, 9), dpi=145, facecolor='#061b33')
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([WEST, EAST, SOUTH, NORTH], crs=ccrs.PlateCarree())
    # Intentionally no land imagery: Jamaica is white as requested.
    vmin = 0.0 if layer != 'sst' else float(np.nanpercentile(spd, 2))
    vmax = max(2.0, float(np.nanpercentile(spd, 99))) if layer == 'currents' else float(np.nanpercentile(spd, 98))
    if vmax <= vmin: vmax = vmin + 1.0
    # Upsample and softly blend the existing model grid for display only.
    # This smooths block edges; it does NOT increase the model's actual resolution.
    # Normalized smoothing respects missing ocean data and avoids treating NaNs as zero.
    valid = np.isfinite(spd)
    filled = np.where(valid, spd, 0.0)
    scale_factor = 5
    hi_value = zoom(filled, scale_factor, order=3, mode='nearest')
    hi_weight = zoom(valid.astype(float), scale_factor, order=1, mode='nearest')
    hi_value = gaussian_filter(hi_value * hi_weight, sigma=1.15)
    hi_weight = gaussian_filter(hi_weight, sigma=1.15)
    hi_spd = np.ma.masked_where(hi_weight < .85,
                                hi_value / np.maximum(hi_weight, 1e-9))
    hi_lons = np.linspace(float(lons[0]), float(lons[-1]), hi_spd.shape[1])
    hi_lats = np.linspace(float(lats[0]), float(lats[-1]), hi_spd.shape[0])
    mesh = ax.pcolormesh(hi_lons, hi_lats, hi_spd,
                         transform=ccrs.PlateCarree(), cmap='turbo',
                         shading='gouraud', vmin=vmin, vmax=vmax,
                         alpha=.96, rasterized=True, zorder=2)
    # White land overlays the ocean current field; no satellite or terrain imagery.
    ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='white', edgecolor='none', zorder=4)
    ax.coastlines(resolution='10m', linewidth=.85, color='#27465e', zorder=5)
    # Thin outline keeps the island identifiable even where forecast pixels
    # overlap a coastline.
    ax.add_feature(cfeature.BORDERS, linewidth=.3, edgecolor='#d8e9ef', zorder=4)
    step = max(1, int(max(len(lons),len(lats))/28))
    if layer == 'currents':
        ax.quiver(lons[::step], lats[::step], uvals[::step,::step], vvals[::step,::step],
                  transform=ccrs.PlateCarree(), color='white', alpha=.85,
                  scale=12, width=.0022, headwidth=3.7, headlength=5.5, zorder=3)
    elif layer == 'waves':
        # VMDR is direction waves COME FROM; arrows point in travel direction.
        angle = np.deg2rad(wave_dir + 180)
        wu = np.sin(angle); wv = np.cos(angle)
        ax.quiver(lons[::step], lats[::step], wu[::step,::step], wv[::step,::step],
                  transform=ccrs.PlateCarree(), color='white', alpha=.85,
                  scale=36, width=.0022, headwidth=3.7, headlength=5.5, zorder=3)
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
    # Minimal map: preserve the current-speed color scale and model timestamp, omit explanatory text.
    ax.set_title('JAMAICA MARINE WEATHER  |  ' + key.upper() + ' ' + {'currents':'CURRENTS','sst':'SEA TEMPERATURE','waves':'WAVE HEIGHT'}[layer] + '\n'
                 + 'Model time: ' + source_time,
                 fontsize=15, weight='bold', color='white', pad=17)
    # Inset legend INSIDE the map, at lower right (not in the outside black margin).
    # A restrained backdrop prevents the colour scale and its labels from crossing
    # map labels or disappearing against the ocean-current colours.
    legend_panel = FancyBboxPatch((.625, .018), .36, .132,
        boxstyle='round,pad=0.006,rounding_size=0.014',
        transform=ax.transAxes, facecolor='#061b33', edgecolor='#ffffff',
        linewidth=.55, alpha=.88, zorder=20, clip_on=False)
    ax.add_patch(legend_panel)
    ax.text(.65, .119, {'currents':'Current speed (knots)','sst':'Sea temperature (°C)','waves':'Wave height (metres)'}[layer], transform=ax.transAxes,
            color='white', fontsize=9, fontweight='bold', zorder=22)
    legend_ax = ax.inset_axes([.65, .075, .31, .023], zorder=22)
    cb = fig.colorbar(mesh, cax=legend_ax, orientation='horizontal')
    cb.ax.tick_params(labelcolor='white', color='white', labelsize=7,
                      length=2, pad=2)
    cb.outline.set_edgecolor('white')
    # Arrows show where the water is travelling (not where it comes from).
    ax.text(.65, .031, {'currents':'→  Current flow direction','sst':'Sea surface temperature','waves':'→  Wave travel direction'}[layer], transform=ax.transAxes,
            color='white', fontsize=7.6, zorder=22)

    filename = f'{layer}-{key}.png'
    fig.savefig(OUT / filename, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    return {
        'key': key, 'label': {'current':'Current', 'tomorrow':'Tomorrow', 'weekend':'Weekend'}[key],
        'image': filename, 'model_time_utc': source_time,
        'target_jamaica': target.isoformat(),
        'model_time_jamaica': actual_utc.astimezone(TZ).strftime('%a %d %b %Y, %I:%M %p Jamaica'),
    }

layers = {}
for layer, label in [('currents', 'Ocean Currents'), ('sst', 'Sea Surface Temperature'),
                     ('waves', 'Wave Height & Direction')]:
    try:
        forecasts = [generate_one(k, v, layer) for k, v in forecast_targets(now_local).items()]
        layers[layer] = {'label': label, 'forecasts': forecasts}
        print(f'{layer}: generated {len(forecasts)} forecast maps')
    except Exception as exc:
        # Current maps are essential; never publish a new site without them.
        if layer == 'currents':
            raise
        # If one optional layer fails, do not publish partially-generated images.
        for key in ('current', 'tomorrow', 'weekend'):
            (OUT / f'{layer}-{key}.png').unlink(missing_ok=True)
        layers[layer] = {'label': label, 'forecasts': [], 'error': f'{label} temporarily unavailable'}
        print(f'WARNING: {label} not published: {exc}')
metadata = {
    'version': '3.8.8', 'dataset': DATASET,
    'generated_utc': datetime.now(timezone.utc).isoformat(),
    'bank_count': len(banks), 'data_provider': 'Copernicus Marine',
    'display_units': 'knots', 'native_grid_unchanged': True,
    'forecasts': layers['currents']['forecasts'],  # Backward compatibility
    'layers': layers,
}
(OUT / 'forecast.json').write_text(json.dumps(metadata, indent=2))
shutil.copyfile(OUT / 'currents-tomorrow.png', OUT / 'currents.png')
(OUT / 'index.html').write_text(PAGE, encoding='utf-8')
print('Generated layer status:', {k: len(v['forecasts']) for k,v in layers.items()})
