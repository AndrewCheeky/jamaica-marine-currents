"""Generate a Jamaica chlorophyll-a observation map from Copernicus daily L4 ocean colour.
No forecasts or fabricated data. Optional layer: failures do not interrupt other maps.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib import patheffects as pe
from PIL import Image
import copernicusmarine

LOG = logging.getLogger(__name__)


def generate_chlorophyll(out, root, banks, bounds, dataset_id, username, password):
    out, root = Path(out), Path(root)
    image_path = out / 'chlorophyll-latest.png'
    metadata_path = out / 'chlorophyll.json'
    previous = {}
    if metadata_path.exists():
        try:
            previous = json.loads(metadata_path.read_text())
        except (ValueError, OSError):
            pass
    try:
        west, east, south, north = bounds
        now = datetime.now(timezone.utc)
        # Ocean-colour daily NRT has a publication delay and a short rolling archive.
        # Request recent days and select the actual latest returned timestamp.
        ds = copernicusmarine.open_dataset(
            dataset_id=dataset_id, variables=['CHL'],
            minimum_longitude=west, maximum_longitude=east,
            minimum_latitude=south, maximum_latitude=north,
            start_datetime=(now-timedelta(days=8)).strftime('%Y-%m-%dT00:00:00'),
            end_datetime=now.strftime('%Y-%m-%dT23:59:59'),
            username=username, password=password,
        )
        if 'time' not in ds.coords or ds.sizes.get('time', 0) == 0:
            raise ValueError('No observation timestamps returned')
        # Avoid assuming dataset timestamps match the workflow run date.
        times = np.asarray(ds['time'].values).astype('datetime64[s]')
        latest = times[np.isfinite(times.astype(float))].max()
        selected = ds.sel(time=latest)
        if 'CHL' not in selected:
            raise ValueError('CHL variable absent')
        field = selected['CHL'].squeeze(drop=True)
        lat_key = 'latitude' if 'latitude' in field.coords else 'lat'
        lon_key = 'longitude' if 'longitude' in field.coords else 'lon'
        lats = np.asarray(field[lat_key].values, dtype=float)
        lons = np.asarray(field[lon_key].values, dtype=float)
        values = np.asarray(field.values, dtype=float)
        if values.shape != (len(lats), len(lons)) or values.ndim != 2:
            raise ValueError('Unexpected CHL grid dimensions')
        valid = np.isfinite(values) & (values > 0)
        if valid.sum() < 10:
            raise ValueError('Insufficient valid CHL pixels')
        from matplotlib.colors import LogNorm
        fig = plt.figure(figsize=(13.5, 9), dpi=145, facecolor='#061b33')
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_extent([west,east,south,north], crs=ccrs.PlateCarree())
        ax.set_facecolor('#061b33')
        mesh = ax.pcolormesh(lons, lats, np.ma.masked_where(~valid,values),
                            cmap='viridis', norm=LogNorm(vmin=.03,vmax=5),
                            shading='auto', transform=ccrs.PlateCarree(), zorder=1)
        ax.add_feature(cfeature.LAND, facecolor='white', edgecolor='#516b7f', linewidth=.7, zorder=4)
        ax.coastlines(resolution='10m', color='#516b7f', linewidth=.6, zorder=5)
        icon = np.asarray(Image.open(root/'site/assets/fish-pin.png').convert('RGBA').resize((13,20),Image.Resampling.LANCZOS))
        for bank in banks:
            lon,lat = float(bank['lon']),float(bank['lat'])
            if west <= lon <= east and south <= lat <= north:
                ax.add_artist(AnnotationBbox(OffsetImage(icon,zoom=1),(lon,lat),xycoords='data',frameon=False,pad=0,zorder=7))
                label=ax.annotate(bank['name'],(lon,lat),xytext=(9,-7),textcoords='offset points',fontsize=7.3,color='white',fontweight='bold',zorder=8)
                label.set_path_effects([pe.withStroke(linewidth=2.5,foreground='#061b33')])
        date = np.datetime_as_string(latest,unit='D')
        ax.set_title('JAMAICA MARINE WEATHER  |  CHLOROPHYLL-a\nSatellite observation: '+date+' UTC',
                     color='white', fontsize=15, weight='bold', pad=17)
        cax = ax.inset_axes([.63,.045,.33,.026],zorder=12)
        cb=fig.colorbar(mesh,cax=cax,orientation='horizontal')
        cb.ax.tick_params(labelcolor='white',color='white',labelsize=8)
        cb.outline.set_edgecolor('white')
        ax.text(.63,.085,'Chlorophyll-a (mg/m³) · logarithmic scale',transform=ax.transAxes,color='white',fontsize=9,fontweight='bold',zorder=12,
                path_effects=[pe.withStroke(linewidth=2,foreground='#061b33')])
        tmp=out/'chlorophyll-latest.tmp.png'
        try:
            fig.savefig(tmp,bbox_inches='tight',facecolor=fig.get_facecolor())
            with Image.open(tmp) as check: check.verify()
            tmp.replace(image_path)
        finally:
            plt.close(fig)
            tmp.unlink(missing_ok=True)
        result={'image':image_path.name,'observation_date':date,'status':'latest_observation','dataset_id':dataset_id}
        metadata_path.write_text(json.dumps(result,indent=2))
        print('Copernicus chlorophyll-a: observation',date)
        return result
    except Exception as exc:
        # Never mislabel an old image as today's satellite observation.
        print('WARNING: Copernicus chlorophyll-a unavailable:',str(exc)[:300])
        if image_path.exists() and previous.get('observation_date') and previous.get('image')==image_path.name:
            result={**previous,'status':'previous_observation'}
        else:
            result={'image':None,'observation_date':None,'status':'unavailable'}
        metadata_path.write_text(json.dumps(result,indent=2))
        return result
