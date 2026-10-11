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
CHL_DATASET = os.environ.get('COPERNICUS_CHL_DATASET_ID', 'cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D')
USERNAME = os.environ['COPERNICUSMARINE_SERVICE_USERNAME']
PASSWORD = os.environ['COPERNICUSMARINE_SERVICE_PASSWORD']
# Geographic bounds must be checked against all banks when the complete list is supplied.
WEST, EAST, SOUTH, NORTH = -79.5, -74.5, 16.0, 20.0
import shutil

PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jamaica Marine Weather | Ocean Overlays</title><style>:root{color-scheme:light}*{box-sizing:border-box}body{font:16px system-ui,Arial,sans-serif;background:#f4f8fc;color:#12253a;margin:0;padding:16px}main{max-width:1200px;margin:auto}h1{font-size:clamp(1.3rem,3vw,2rem);margin:8px 0 14px}[hidden]{display:none!important}nav{display:flex;flex-wrap:wrap;gap:9px;margin:0 0 12px}button,select{border:1px solid #aec4d6;background:white;color:#163553;border-radius:8px;padding:11px 14px;font:inherit;cursor:pointer}button[aria-pressed="true"]{background:#123c63;color:white;border-color:#123c63}select{min-width:260px;max-width:100%}label{display:block;margin-bottom:6px;font-weight:650}img{display:block;width:100%;height:auto;border-radius:10px;background:#061b33}#time{margin:8px 0 12px;color:#344c65;font-weight:600}body:has(#layer option[value="chlorophyll"]:checked) #time{text-align:center}small{color:#536879}p{line-height:1.45}.controls{margin:0 0 14px}.notice{color:#a44900}#map[aria-busy="true"]{opacity:.55}</style><style>\n.local-forecast{margin-top:32px;padding-top:22px;border-top:2px solid #d7e4ef}\n.local-forecast h2{font-size:clamp(1.3rem,2.8vw,1.8rem);color:#123c63;margin:0 0 8px}\n.local-forecast .intro{color:#415d77;margin:0 0 18px}\n.forecast-panels{display:grid;grid-template-columns:1fr;gap:20px}\n.forecast-panel{border:1px solid #d3e2ee;border-radius:14px;background:#fff;padding:16px;box-shadow:0 3px 12px rgba(17,45,76,.06)}\n.forecast-panel h3{color:#123c63;font-size:1.16rem;margin:0 0 7px}\n.forecast-panel p{margin:0 0 12px;color:#486077;font-size:.94rem}\n.forecast-frame{display:block;width:100%;border:1px solid #d5e1eb;border-radius:8px;background:#fff}\n.forecast-frame.bulletin{height:560px}.forecast-frame.wind{height:650px;border:3px solid #061b33;border-radius:10px;box-shadow:0 0 0 1px #061b33}\n.source-note{margin-top:14px;font-size:.85rem;color:#536879}\n@media(max-width:640px){body{padding:10px}.forecast-panel{padding:10px}.forecast-frame.bulletin{height:540px}.forecast-frame.wind{height:490px}}\n</style></head><body><main><h1>Jamaica Marine Weather — Ocean Overlays</h1><div class="controls"><label for="layer">Choose marine overlay</label><select id="layer"><option value="currents">Ocean Currents · Existing</option><option value="sst">Sea Surface Temperature · Phase 1</option><option value="waves">Wave Height &amp; Direction · Phase 1</option><option value="sargassum">Sargassum / Possible Weedlines · USF</option><option value="persistent">Persistent Weedlines · 7-day USF indicator</option><option disabled>──────── Future overlays ────────</option><option value="chlorophyll">Pelagic Fishing Intelligence Map</option><option value="opportunities">Fishing Opportunities · Banks &amp; Methods</option><option value="eddies">Ocean Eddies · Sea Level &amp; Currents</option><option disabled>Swell Period · Phase 2</option><option disabled>Subsurface Currents · Phase 3</option><option disabled>Salinity · Phase 3</option><option disabled>Ocean Fronts · Phase 3</option></select></div><div id="fad-controls" hidden><label for="fad-period">Satellite composite</label><select id="fad-period"><option value="7day" selected>FAD 7DAY MEAN</option><option value="1day">FAD 1DAY</option></select><p id="fad-note" aria-live="polite"></p></div><div id="persistence-info" hidden role="note" style="padding:12px 14px;margin:10px 0;background:#eaf3fa;border-left:4px solid #1674a5;border-radius:7px"><strong>7-day floating-algae persistence indicator</strong><p style="margin:7px 0">This view displays the published USF FAD 7DAY MEAN image. Areas of elevated average floating-algae density may warrant investigation, but this is <strong>not a verified count of days with algae</strong>. The same algae may drift; cloud cover and gaps affect observations.</p><p style="margin:7px 0">Compare with <strong>Sargassum / Possible Weedlines → FAD 1DAY</strong> for the latest daily observation. Red, orange and yellow in the source image represent its published density colours, <strong>not</strong> 3+, 2–3 or 1-day persistence categories.</p><small>Source: University of South Florida. Satellite observations only; not a weedline or fish forecast. Not for navigation.</small></div><div id="bathy-controls" hidden style="margin:10px 0;padding:12px 14px;background:#eaf3fa;border-radius:8px"><label style="display:flex;align-items:center;gap:10px"><input type="checkbox" id="bathy-toggle"> Show bathymetric contours (200, 500, 1,000, 2,000 m)</label><small id="bathy-note">Generalized ocean-floor depth zones, not navigation soundings. Not for navigation.</small></div><div id="opportunity-controls" hidden style="margin:12px 0;padding:14px;background:#eaf3fa;border-radius:9px"><label for="fishing-method">Fishing method</label><select id="fishing-method"><option value="trolling">Offshore trolling</option><option value="jigging">Vertical jigging</option><option value="bottom">Bottom fishing</option></select><label for="fishing-bank" style="margin-top:10px">Fishing bank</label><select id="fishing-bank"></select><div id="opportunity-detail" role="status" style="margin-top:12px;line-height:1.5"></div><small>Experimental opportunity index (0–100), not a percentage chance of catching fish. Heuristic weights have not been validated with Jamaican catch data. Not for navigation.</small></div><nav id="forecast-controls" aria-label="Forecast period"><button type="button" data-period="current" aria-pressed="true">Current</button><button type="button" data-period="tomorrow" aria-pressed="false">Tomorrow</button><button type="button" data-period="weekend" aria-pressed="false">Weekend</button></nav><p id="time" aria-live="polite">Loading forecast metadata…</p><img id="map" src="currents-current.png" alt="Current ocean currents forecast for Jamaica with 13 location markers"><p id="message" class="notice" role="status"></p><p><small>Copernicus Marine forecast models · Model timestamps shown for each forecast · <span id="updated">Last updated: loading…</span> · Not for navigation.</small></p><section class="local-forecast" aria-labelledby="local-forecast-heading">\n<h2 id="local-forecast-heading">🌊 Local Marine Forecast</h2>\n<p class="intro">Jamaica marine forecast bulletin and animated wind outlook. Content is supplied by Jamaica Met Office.</p>\n<div class="forecast-panels">\n<article class="forecast-panel"><h3>Marine Forecast Bulletin</h3>\n<p>Local marine conditions, coastal waters and marine warnings</p>\n<iframe class="forecast-frame bulletin" title="Jamaica local marine forecast bulletin" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" src="https://jamaica.weatherproof.fi/web/website_2014/website_elements/news2.php?type=6"></iframe>\n</article>\n<article class="forecast-panel"><h3>Animated Wind Forecast</h3>\n<p>Wind forecast animation and controls</p>\n<iframe class="forecast-frame wind" title="Jamaica animated wind forecast" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" allow="fullscreen" src="https://jamaica.weatherproof.fi/web/marine2.php"></iframe>\n</article>\n</div>\n<p class="source-note">Not for navigation.</p>\n</section><footer style="margin:30px 0 12px;padding:18px 0;border-top:1px solid #cbdbe8;text-align:center;color:#415d77;font-size:.9rem">Helping Jamaica's fisherfolk make better-informed decisions about where, when and how to fish. © Andrew 'Cheeky'</footer></main><script>(async()=>{
const status=document.querySelector('#time'),map=document.querySelector('#map'),layer=document.querySelector('#layer'),msg=document.querySelector('#message'),fadControls=document.querySelector('#fad-controls'),fadPeriod=document.querySelector('#fad-period'),fadNote=document.querySelector('#fad-note'),forecastControls=document.querySelector('#forecast-controls'),persistenceInfo=document.querySelector('#persistence-info'),bathyControls=document.querySelector('#bathy-controls'),bathyToggle=document.querySelector('#bathy-toggle'),bathyNote=document.querySelector('#bathy-note'),opportunityControls=document.querySelector('#opportunity-controls'),fishingMethod=document.querySelector('#fishing-method'),fishingBank=document.querySelector('#fishing-bank'),opportunityDetail=document.querySelector('#opportunity-detail');
let data=null, fad=null, period='current';
const fmt=(iso)=>{if(!iso)return 'Unknown';const d=new Date(iso+'T12:00:00Z');return Number.isNaN(d.getTime())?iso:new Intl.DateTimeFormat('en-JM',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(d)};
function displayImage(src,alt){map.hidden=false;map.setAttribute('aria-busy','true');const next=new Image();next.onload=()=>{map.src=next.src;map.alt=alt;map.removeAttribute('aria-busy')};next.onerror=()=>{map.hidden=true;map.removeAttribute('aria-busy');msg.textContent='Satellite image could not be loaded. Please try again later.'};next.src=src;}
function show(){const isFad=layer.value==='sargassum',isPersistent=layer.value==='persistent';fadControls.hidden=!isFad;persistenceInfo.hidden=!isPersistent;forecastControls.hidden=isFad||isPersistent||['chlorophyll','opportunities','eddies'].includes(layer.value);opportunityControls.hidden=layer.value!=='opportunities';bathyControls.hidden=layer.value!=='chlorophyll';
if(isPersistent){const view=fad?.views?.['7day'];if(!view?.image){map.hidden=true;status.textContent='7-day floating-algae imagery unavailable';msg.textContent='No verified seven-day satellite observation is available. The standard Sargassum and other marine maps remain accessible.';return;}const range=view.observation_start&&view.observation_start!==view.observation_end?fmt(view.observation_start)+' to '+fmt(view.observation_end):fmt(view.observation_end||view.observation_date);status.textContent='Persistent Weedlines · USF FAD 7DAY MEAN · Observations: '+range;msg.textContent=(view.status==='previous_observation'?'Last successful satellite image retained; algae may have moved. ':'')+'Seven-day mean density is a persistence indicator, not a day-by-day detection count. Satellite coverage may be incomplete.';displayImage(view.image+'?observed='+encodeURIComponent(view.observation_end||''),'USF seven-day mean floating algae density for Jamaica, '+range+'. This is not a measured count of persistent days.');return;}
if(isFad){const view=fad?.views?.[fadPeriod.value];fadNote.textContent='Source: University of South Florida (USF). Satellite observations, not a weedline forecast.';
if(!view?.image){map.hidden=true;status.textContent='Satellite imagery is currently unavailable.';msg.textContent='No verified '+(fadPeriod.value==='1day'?'daily':'seven-day')+' observation is available. Other marine maps remain available.';return;}
const range=view.observation_start&&view.observation_start!==view.observation_end?fmt(view.observation_start)+' to '+fmt(view.observation_end):fmt(view.observation_end||view.observation_date);
status.textContent=(fadPeriod.value==='1day'?'FAD 1DAY':'FAD 7DAY MEAN')+' · Satellite observations: '+range;
msg.textContent=view.status==='previous_observation'?'Showing the last successfully retrieved satellite observation. Floating algae may have moved.':'';
displayImage(view.image+'?observed='+encodeURIComponent(view.observation_end||''),'USF Jamaica floating algae density satellite observations, '+range);return;}
if(layer.value==='opportunities'){
 const view=data?.fishing_opportunities;
 if(!view||view.status!=='available'||!view.banks?.length){map.hidden=true;status.textContent='Fishing-bank conditions temporarily unavailable';msg.textContent='Existing marine maps remain available.';opportunityDetail.textContent='No verified numerical bank conditions available.';return;}
 if(!fishingBank.options.length){view.banks.forEach(b=>{const o=document.createElement('option');o.value=b.key;o.textContent=b.name;fishingBank.appendChild(o);});}
 const b=view.banks.find(b=>b.key===fishingBank.value)||view.banks[0];const method=view.methods[fishingMethod.value];
 const format=x=>x===null||x===undefined?'Unavailable':x;
 opportunityDetail.replaceChildren();
 const add=(label,value)=>{const p=document.createElement('p');p.style.margin='5px 0';const strong=document.createElement('strong');strong.textContent=label+': ';p.append(strong,document.createTextNode(String(value)));opportunityDetail.appendChild(p)};
 const h=document.createElement('h3');h.textContent='Environmental Opportunity Scores (experimental)';opportunityDetail.appendChild(h);
 add('Overall bank opportunity index',b.overall_score===null?'Insufficient data':b.overall_score+'/100');
 add('Best-supported group / method',(b.best_supported_species||'Unavailable')+' / '+(b.best_method||'Unavailable'));
 const ms=b.method_scores?.[fishingMethod.value];add('Selected method index',ms===null||ms===undefined?'Insufficient data':ms+'/100');
 const table=document.createElement('table');table.style.cssText='width:100%;border-collapse:collapse;margin:10px 0';
 const header=document.createElement('tr');['Species group','Index / 100','Data completeness'].forEach(x=>{const th=document.createElement('th');th.textContent=x;th.style.cssText='text-align:left;border-bottom:1px solid #a7bbcc;padding:6px';header.appendChild(th)});table.appendChild(header);
 Object.values(b.species_scores||{}).filter(x=>x.method===fishingMethod.value).sort((a,b)=>(b.score??-1)-(a.score??-1)).forEach(x=>{const tr=document.createElement('tr');[x.label,x.score===null?'Insufficient data':x.score+'/100',x.data_completeness_pct+'%'].forEach(y=>{const td=document.createElement('td');td.textContent=y;td.style.cssText='padding:6px;border-bottom:1px solid #dae5ed';tr.appendChild(td)});table.appendChild(tr)});opportunityDetail.appendChild(table);
 add('SST',format(b.sst_c)+' °C');add('Surface current',format(b.current_knots)+' knots');
 add('Chlorophyll-a',b.chlorophyll_mg_m3===null?'Unavailable':b.chlorophyll_mg_m3+' mg/m³');
 add('Chlorophyll front',b.chlorophyll_front_nearby===null?'Unavailable':b.chlorophyll_front_nearby?'Elevated gradient nearby':'Not elevated');
 add('Seabed depth (GEBCO)',b.depth_m===null?'Unavailable':b.depth_m+' m (approximate)');
 add('Thermal front',b.thermal_boundary_nearby?'Elevated gradient nearby':'Not elevated');
 add('Chlorophyll observation date',fmt(b.chlorophyll_date));
 add('Current observation date',fmt((b.current_time_utc||'').slice(0,10)));
 add('SST observation date',fmt((b.sst_time_utc||'').slice(0,10)));
 const note=document.createElement('p');note.style.cssText='font-size:.9em;color:#5a4760';note.textContent='These 0–100 indices use experimental environmental rules and are NOT catch probabilities. Scores exclude unavailable inputs and display completeness. Weedlines and eddies are not yet numerically scored.';opportunityDetail.appendChild(note);
 status.textContent='Fishing Opportunities · '+b.name+' · '+method.label;
 msg.textContent='Experimental environmental opportunity index, not catch probability. Chlorophyll and GEBCO depth are included where available. No numerical weedline or eddy scoring. Not for navigation.';
 const base=view.image||data?.chlorophyll?.image||data?.layers?.sst?.forecasts?.find(x=>x.key==='current')?.image;
 if(base)displayImage(base,'Regional environmental context around Jamaica, select a bank for numerical conditions');else map.hidden=true;
 return;}
 if(layer.value==='eddies'){
 const view=data?.ocean_eddies;if(!view?.image){map.hidden=true;status.textContent='Ocean eddy observations unavailable';msg.textContent=view?.description||'Sea-level data temporarily unavailable; existing maps remain accessible.';return;}
 status.textContent='Ocean Eddies · Satellite observation: '+fmt(view.observation_date);
 msg.textContent='Blue: lower sea-level anomaly; red: higher. White arrows: geostrophic currents. Rotating features are candidates, not verified eddy boundaries. Not for navigation.';
 displayImage(view.image+'?observed='+encodeURIComponent(view.observation_date),'Jamaica satellite sea-level anomaly and geostrophic currents');return;}
 if(layer.value==='chlorophyll'){
const view=data?.chlorophyll;
if(!view?.image){map.hidden=true;status.textContent='Chlorophyll-a observations are currently unavailable.';msg.textContent='The latest verified satellite map could not be retrieved. Other marine maps remain available.';return;}
status.textContent='Pelagic composite · Chlorophyll: '+fmt(view.observation_date)+' · SST: '+fmt(view.sst_date)+' · Currents: '+fmt(view.current_date)+' · Zooplankton: '+fmt(view.zooplankton_date);
msg.textContent='Chlorophyll background + white chlorophyll fronts'+(view.sst_status==='available'?' + orange thermal fronts':'')+(view.convergence_status==='available'?' + cyan current convergence':'')+(view.zooplankton_status==='available'?' + magenta zooplankton':'')+'. Outlines mark strong transitions, not the entire enclosed area. Nearshore detections may be unreliable. Missing optional indicators are omitted. Environmental planning only, not a fish forecast.'+(view.status==='previous_observation'?' Showing the last successfully retrieved observation.':'');
const bathyReady=Boolean(view.bathymetry_image);bathyToggle.disabled=!bathyReady;bathyNote.textContent=bathyReady?'Generalized Natural Earth 10m depth-zone boundaries: '+(view.bathymetry_depths_m||[]).join(', ')+' m. Not for navigation.':'Bathymetry is temporarily unavailable; standard composite remains available.';const selected=bathyReady&&bathyToggle.checked;displayImage((selected?view.bathymetry_image:view.image)+'?observed='+encodeURIComponent(view.observation_date||''),'Pelagic intelligence around Jamaica '+(selected?'with generalized bathymetric contours':'without bathymetry')+', chlorophyll observation '+fmt(view.observation_date));return;}
const item=data?.layers?.[layer.value],f=item?.forecasts?.find(x=>x.key===period);
document.querySelectorAll('button[data-period]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.period===period)));
if(!f){map.hidden=true;status.textContent='This overlay is currently unavailable.';msg.textContent=item?.error||'Try a different overlay.';return;}
msg.textContent='';status.textContent=f.label+' · '+item.label+' · Model time: '+f.model_time_jamaica;displayImage(f.image,f.label+' '+item.label+' map of Jamaica');}
layer.addEventListener('change',show);bathyToggle.addEventListener('change',show);fadPeriod.addEventListener('change',show);fishingMethod.addEventListener('change',show);fishingBank.addEventListener('change',show);document.querySelectorAll('button[data-period]').forEach(b=>b.addEventListener('click',()=>{period=b.dataset.period;show()}));
try{const r=await fetch('forecast.json',{cache:'no-store'});if(!r.ok)throw Error('Forecast metadata unavailable');data=await r.json();const updated=document.querySelector('#updated');if(data.generated_utc){updated.textContent='Last updated: '+new Intl.DateTimeFormat('en-JM',{timeZone:'America/Jamaica',weekday:'short',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:true}).format(new Date(data.generated_utc))+' (Jamaica time)';}else updated.textContent='Last updated: unavailable';fad=data.sargassum||null;
if(!fad){try{const fr=await fetch('sargassum.json',{cache:'no-store'});if(fr.ok)fad=await fr.json()}catch(e){}}
show();}catch(e){status.textContent='Forecast metadata unavailable; displaying last published current map.';document.querySelector('#updated').textContent='Last updated: unavailable';msg.textContent='';}
})();</script></body></html>'''
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
    if key == 'current' and layer in ('currents','sst'):
        try:
            import xarray as _xr
            path=OUT/'opportunities-grids.npz'
            if layer=='currents':
                np.savez_compressed(OUT/'opportunities-current.npz',lats=lats,lons=lons,u=uvals,v=vvals,current_time=actual_utc.isoformat())
            else:
                cp=OUT/'opportunities-current.npz'
                if cp.exists():
                    with np.load(cp) as d:
                        clats=d['lats'];clons=d['lons'];cu=d['u'];cv=d['v'];ct=str(d['current_time'])
                    temp=_xr.DataArray(spd,coords={'latitude':lats,'longitude':lons},dims=['latitude','longitude']).interp(latitude=clats,longitude=clons).values
                    np.savez_compressed(path,lats=clats,lons=clons,u=cu,v=cv,sst=temp,current_time=ct,sst_time=actual_utc.isoformat())
        except Exception as ex:
            print('WARNING: bank grid preparation:',str(ex)[:250])
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
    source_time = actual_utc.astimezone(TZ).strftime('%I:%M %p %d %b %Y Jamaica time')
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
        'model_time_jamaica': actual_utc.astimezone(TZ).strftime('%I:%M %p  %d %b %Y Jamaica time'),
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
try:
    fishing_module=__import__('fishing_opportunities')
    fishing_info=fishing_module.build(OUT,banks)
    if fishing_info.get('status')=='available':
        import opportunity_scoring
        extra=opportunity_scoring.enrich(OUT,banks,(WEST,EAST,SOUTH,NORTH),USERNAME,PASSWORD,CHL_DATASET,ROOT/'jamaica.nc')
        fishing_info=opportunity_scoring.add_scores(fishing_info,extra)
        fishing_info['image']=fishing_module.render_map(OUT,banks)
except Exception as exc:
    print('WARNING: fishing opportunities:',exc)
    fishing_info={'status':'unavailable','banks':[]}
try:
    eddy_info=__import__('ocean_eddies').generate(OUT,banks,(WEST,EAST,SOUTH,NORTH),USERNAME,PASSWORD)
except Exception as exc:
    print('WARNING: ocean eddies:',exc)
    eddy_info={'status':'unavailable','image':None}
for tmp in ('opportunities-current.npz','opportunities-grids.npz'):
    (OUT/tmp).unlink(missing_ok=True)
metadata = {
    'version': '3.8.21', 'dataset': DATASET,
    'generated_utc': datetime.now(timezone.utc).isoformat(),
    'bank_count': len(banks), 'data_provider': 'Copernicus Marine',
    'display_units': 'knots', 'native_grid_unchanged': True,
    'forecasts': layers['currents']['forecasts'],  # Backward compatibility
    'layers': layers,
    'fishing_opportunities': fishing_info,
    'ocean_eddies': eddy_info,
    'sargassum': __import__('usf_fad').generate_fad(OUT),
    'chlorophyll': __import__('composite').generate_composite(OUT, ROOT, banks, (WEST, EAST, SOUTH, NORTH), CHL_DATASET, USERNAME, PASSWORD),
}
(OUT / 'forecast.json').write_text(json.dumps(metadata, indent=2))
shutil.copyfile(OUT / 'currents-tomorrow.png', OUT / 'currents.png')
(OUT / 'index.html').write_text(PAGE, encoding='utf-8')
print('Generated layer status:', {k: len(v['forecasts']) for k,v in layers.items()})
