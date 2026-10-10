"""Observed chlorophyll-a + computed frontal gradients + optional model zooplankton.
No fish predictions or fabricated values. Data validity dates are independent.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib import patheffects as pe
from PIL import Image
from scipy.ndimage import gaussian_filter
from pelagic import indicators, _mask_top
from scipy.spatial import cKDTree
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import copernicusmarine


def _grid(ds, variable):
    if 'time' not in ds.coords or not ds.sizes.get('time'):
        raise ValueError('No timestamps returned')
    times=np.asarray(ds.time.values).astype('datetime64[s]')
    latest=times.max()
    field=ds[variable].sel(time=latest).squeeze(drop=True)
    # Some model products have depth; choose surface layer only.
    for depth in ('depth','deptht','lev'):
        if depth in field.dims: field=field.isel({depth:0})
    lat=next(k for k in ('latitude','lat') if k in field.coords)
    lon=next(k for k in ('longitude','lon') if k in field.coords)
    return (np.asarray(field[lon].values,float),np.asarray(field[lat].values,float),
            np.asarray(field.values,float),np.datetime_as_string(latest,unit='D'))


def _fetch(dataset, variables, bounds, user, password, days=8):
    west,east,south,north=bounds
    now=datetime.now(timezone.utc)
    return copernicusmarine.open_dataset(
        dataset_id=dataset, variables=variables,
        minimum_longitude=west, maximum_longitude=east,
        minimum_latitude=south, maximum_latitude=north,
        start_datetime=(now-timedelta(days=days)).strftime('%Y-%m-%dT00:00:00'),
        end_datetime=now.strftime('%Y-%m-%dT23:59:59'),
        username=user,password=password)


def generate_composite(out, root, banks, bounds, chl_dataset, username, password):
    out,root=Path(out),Path(root)
    image=out/'chlorophyll-latest.png'
    metadata=out/'chlorophyll.json'
    try: previous=json.loads(metadata.read_text())
    except (OSError,ValueError): previous={}
    try:
        lon,lat,chl,chl_date=_grid(_fetch(chl_dataset,['CHL'],bounds,username,password),'CHL')
        if chl.shape!=(len(lat),len(lon)) or np.count_nonzero(np.isfinite(chl)&(chl>0))<10:
            raise ValueError('Insufficient valid chlorophyll observations')
        # Log chlorophyll front strength per km; smooth to avoid single-pixel artifacts.
        logchl=np.log10(np.where(np.isfinite(chl)&(chl>0),chl,np.nan))
        valid=np.isfinite(logchl)
        weight=gaussian_filter(valid.astype(float),1.1)
        smoothed=gaussian_filter(np.nan_to_num(logchl),1.1)/np.maximum(weight,1e-6)
        smoothed[weight<0.7]=np.nan
        dy=np.gradient(lat)*111.2
        dx=np.gradient(lon)[None,:]*111.2*np.cos(np.deg2rad(lat[:,None]))
        gy=np.gradient(smoothed,axis=0)/dy[:,None]
        gx=np.gradient(smoothed,axis=1)/dx
        gradient=np.hypot(gx,gy)
        finite=gradient[np.isfinite(gradient)]
        if finite.size<10: raise ValueError('Insufficient chlorophyll pixels for gradient')
        # Relative contour thresholds adapt to real data, not arbitrary fish-potential scores.
        thresholds=np.unique(np.quantile(finite,[.96]))
        front_mask=_mask_top(gradient,.94,min_pixels=10)
        extra=indicators(bounds,username,password,lon,lat,chl_date,_fetch,_grid)
        zoo=None; zoo_date=None; zoo_error=None
        zoo_dataset=os.getenv('COPERNICUS_ZOO_DATASET_ID','cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m')
        zoo_variable=os.getenv('COPERNICUS_ZOO_VARIABLE','zooc')
        try:
            zlons,zlats,zvalues,zoo_date=_grid(_fetch(zoo_dataset,[zoo_variable],bounds,username,password,days=5),zoo_variable)
            zvalid=np.isfinite(zvalues)&(zvalues>=0)
            if zvalues.shape!=(len(zlats),len(zlons)) or np.count_nonzero(zvalid)<10:
                raise ValueError('Insufficient zooplankton grid values')
            zoo=(zlons,zlats,np.where(zvalid,zvalues,np.nan))
        except Exception as exc:
            zoo_error=str(exc)[:180]
            print('WARNING: optional zooplankton layer unavailable:',zoo_error)
        west,east,south,north=bounds
        fig=plt.figure(figsize=(14,9),dpi=145,facecolor='#07182c')
        ax=plt.axes(projection=ccrs.PlateCarree())
        ax.set_extent([west,east,south,north],crs=ccrs.PlateCarree())
        ax.set_facecolor('#07182c')
        mesh=ax.pcolormesh(lon,lat,np.ma.masked_invalid(np.where(chl>0,chl,np.nan)),
                           norm=LogNorm(vmin=.03,vmax=5),cmap='viridis',shading='auto',
                           transform=ccrs.PlateCarree(),zorder=1)
        # Draw only the highest observed front-strength contours.
        if np.isfinite(front_mask).sum()>4:
            ax.contour(lon,lat,np.isfinite(front_mask).astype(float),levels=[.5],
                       colors=['#ffffff'],linewidths=1.35,
                       transform=ccrs.PlateCarree(),zorder=3)
        if extra['sst_fronts'] is not None:
            slon,slat,sg=extra['sst_fronts']
            ax.contour(slon,slat,np.isfinite(sg).astype(float),levels=[.5],
                       colors=['#ffb347'],linewidths=1.5,
                       transform=ccrs.PlateCarree(),zorder=3)
        if extra['convergence'] is not None:
            clon,clat,cg=extra['convergence']
            ax.contour(clon,clat,np.isfinite(cg).astype(float),levels=[.5],
                       colors=['#48f0ec'],linewidths=1.25,linestyles='dashed',
                       transform=ccrs.PlateCarree(),zorder=3)
        # Small gold circles mark proximity of independently measured chlorophyll
        # and thermal fronts, not a fish probability or a predicted hotspot.
        overlap_count=0
        if extra['sst_fronts'] is not None:
            slon,slat,sg=extra['sst_fronts']
            yy,xx=np.where(np.isfinite(sg))
            cy,cx=np.where(np.isfinite(front_mask))
            if len(xx)>0 and len(cx)>0:
                scale=np.cos(np.deg2rad(np.mean(lat)))
                thermal=np.column_stack((slon[xx]*scale,slat[yy]))
                fronts=np.column_stack((lon[cx]*scale,lat[cy]))
                near=cKDTree(thermal).query(fronts,k=1)[0]<.12  # approximately 13 km
                # Thin densely clustered markers for legibility.
                selected=np.column_stack((lon[cx[near]],lat[cy[near]]))
                if len(selected):
                    kept=[]
                    for x,y in selected:
                        if all(np.hypot((x-a)*scale,y-b)>.18 for a,b in kept):
                            kept.append((x,y))
                        if len(kept)>=18:break
                    if kept:
                        coords=np.asarray(kept)
                        ax.scatter(coords[:,0],coords[:,1],s=38,facecolors='none',
                                   edgecolors='#ffdf65',linewidths=1.4,
                                   transform=ccrs.PlateCarree(),zorder=6)
                        overlap_count=len(kept)
        if zoo is not None:
            zlons,zlats,zvalues=zoo
            zfinite=zvalues[np.isfinite(zvalues)]
            zlevels=np.unique(np.quantile(zfinite,[.65,.85]))
            if len(zlevels) and zlevels[0]<zfinite.max() and zlevels[0]>zfinite.min():
                ax.contour(zlons,zlats,np.ma.masked_invalid(zvalues),levels=zlevels,
                           colors='#ed75ff',linewidths=1.1,linestyles='dashed',
                           transform=ccrs.PlateCarree(),zorder=3)
        ax.add_feature(cfeature.LAND,facecolor='#d9e4e9',edgecolor='#344e62',linewidth=.7,zorder=4)
        ax.coastlines(resolution='10m',color='#344e62',linewidth=.7,zorder=5)
        icon=np.asarray(Image.open(root/'site/assets/fish-pin.png').convert('RGBA').resize((13,20),Image.Resampling.LANCZOS))
        for bank in banks:
            x,y=float(bank['lon']),float(bank['lat'])
            if west<=x<=east and south<=y<=north:
                ax.add_artist(AnnotationBbox(OffsetImage(icon,zoom=1),(x,y),xycoords='data',frameon=False,pad=0,zorder=7))
                label=ax.annotate(bank['name'],(x,y),xytext=(8,-8),textcoords='offset points',fontsize=7.2,color='white',fontweight='bold',zorder=8)
                label.set_path_effects([pe.withStroke(linewidth=2.6,foreground='#07182c')])
        fig.suptitle('JAMAICA  |  PELAGIC FISHING INTELLIGENCE',color='white',fontsize=16,fontweight='bold',y=.97)
        fig.text(.12,.91,'Chl: '+chl_date+' | SST: '+(extra['sst_date'] or 'unavailable')+' | Currents: '+(extra['current_date'] or 'unavailable')+' | Zoo: '+(zoo_date or 'unavailable'),color='#e6f1ff',fontsize=10)
        cax=fig.add_axes([.63,.075,.29,.023]); cb=fig.colorbar(mesh,cax=cax,orientation='horizontal')
        cb.ax.tick_params(colors='white',labelsize=8);cb.outline.set_edgecolor('white')
        fig.text(.63,.108,'Chlorophyll-a (mg/m³) · log scale',color='white',fontsize=9)
        fig.text(.12,.10,'White: chl fronts | Orange: SST fronts | Cyan: convergence | Magenta: zoo | Gold rings: overlapping fronts',color='white',fontsize=9)
        fig.text(.12,.07,'Environmental indicators only. Not a fish-location forecast. Not for navigation.',color='#cbd5e1',fontsize=8)
        temp=out/'chlorophyll-latest.tmp.png'
        try:
            fig.savefig(temp,facecolor=fig.get_facecolor(),dpi=145)
            with Image.open(temp) as check: check.verify()
            temp.replace(image)
        finally:
            plt.close(fig);temp.unlink(missing_ok=True)
        result={'image':image.name,'observation_date':chl_date,'zooplankton_date':zoo_date,
                'zooplankton_status':'available' if zoo is not None else 'unavailable',
                'status':'latest_observation','dataset_id':chl_dataset,'zooplankton_dataset_id':zoo_dataset,
                'composite':True,'sst_date':extra['sst_date'],'current_date':extra['current_date'],
                'sst_status':'available' if extra['sst_fronts'] is not None else 'unavailable',
                'convergence_status':'available' if extra['convergence'] is not None else 'unavailable',
                'overlap_front_markers':overlap_count}
        metadata.write_text(json.dumps(result,indent=2))
        print('Copernicus composite: chlorophyll',chl_date,'zooplankton',zoo_date or 'unavailable')
        return result
    except Exception as exc:
        print('WARNING: Copernicus composite unavailable:',str(exc)[:300])
        if image.exists() and previous.get('observation_date') and previous.get('image')==image.name:
            result={**previous,'status':'previous_observation'}
        else: result={'image':None,'observation_date':None,'status':'unavailable','composite':True}
        metadata.write_text(json.dumps(result,indent=2))
        return result
