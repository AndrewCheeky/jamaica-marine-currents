"""Experimental ocean-front diagnostics on native Copernicus forecast grids.

Produces a transparent-feature map, GeoJSON candidates and daily persistence
records. Features are model diagnostics, not fish locations or navigation data.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter, minimum_filter

VERSION = '3.9.2'
KINDS = ('sst_front', 'convergence', 'shear', 'eddy_candidate')
LABELS = {'sst_front':'Temperature front','convergence':'Current convergence',
          'shear':'Current shear','eddy_candidate':'Possible eddy / rotation'}
COLORS = {'sst_front':'#ffbd55','convergence':'#55e0ed',
          'shear':'#f08aff','eddy_candidate':'#bba0ff'}

def _smooth(a, sigma=1):
    a=np.asarray(a,dtype=float)
    valid=np.isfinite(a)
    if not valid.any(): return np.full_like(a,np.nan)
    weights=gaussian_filter(valid.astype(float),sigma)
    return np.where(weights>0.45, gaussian_filter(np.where(valid,a,0),sigma)/np.maximum(weights,1e-9),np.nan)

def diagnostics(lats,lons,sst,u,v):
    """Derivatives in metric distances; mask missing cells and coastal neighbours."""
    lat=np.asarray(lats,float);lon=np.asarray(lons,float)
    if lat.ndim!=1 or lon.ndim!=1 or min(len(lat),len(lon))<5:
        raise ValueError('Insufficient geospatial grid resolution')
    shape=(len(lat),len(lon))
    for a in (sst,u,v):
        if np.shape(a)!=shape: raise ValueError('Grid alignment mismatch')
    # Native spacing in metres; x spacing varies with latitude.
    dy=np.gradient(lat)*111_195.0
    dx=np.gradient(lon)[None,:]*111_195.0*np.cos(np.deg2rad(lat))[:,None]
    if np.any(np.abs(dy)<100) or np.any(np.abs(dx)<100): raise ValueError('Invalid grid spacing')
    t,uu,vv=(_smooth(a) for a in (sst,u,v))
    def grad(a):
        gy=np.gradient(a,axis=0)/dy[:,None]
        gx=np.gradient(a,axis=1)/dx
        return gx,gy
    tx,ty=grad(t);ux,uy=grad(uu);vx,vy=grad(vv)
    # SST front °C per 100 km, other diagnostics s^-1 scaled to micro/s.
    fields={'sst_front':np.hypot(tx,ty)*100_000,
            'convergence':-(ux+vy)*1e6,
            'shear':np.hypot(uy,vx)*1e6,
            'eddy_candidate':np.abs(vx-uy)*1e6}
    valid=np.isfinite(sst)&np.isfinite(u)&np.isfinite(v)
    # Exclude cells bordering land or missing input: prevents false coast fronts.
    valid &= minimum_filter(valid.astype(np.uint8),size=3,mode='constant')==1
    for name,arr in fields.items():
        arr[~valid]=np.nan
        if name=='convergence': arr[arr<=0]=np.nan
    return fields

def _candidates(fields,lats,lons,banks,bank_radius_km=45,limit=4):
    lat=np.asarray(lats);lon=np.asarray(lons)
    yy,xx=np.meshgrid(lat,lon,indexing='ij')
    result=[]; by_bank={}
    for bank in banks:
        km=np.hypot((yy-bank['lat'])*111.195,(xx-bank['lon'])*111.195*np.cos(np.deg2rad(bank['lat'])))
        within=km<=bank_radius_km
        picks=[]
        for kind,arr in fields.items():
            vals=arr[within&np.isfinite(arr)]
            if len(vals)<3:continue
            # Strongest 15% of positive local diagnostic values; no catch probability.
            threshold=np.percentile(vals,85)
            if threshold<=0:continue
            eligible=np.where(within&(arr>=threshold)&np.isfinite(arr),arr,-np.inf)
            inds=np.argwhere(eligible>0)
            inds=sorted(inds,key=lambda ij:float(eligible[tuple(ij)]),reverse=True)
            chosen=[]
            for i,j in inds:
                if any(np.hypot((lat[i]-lat[ii])*111.195,(lon[j]-lon[jj])*111.195*np.cos(np.deg2rad(lat[i])))<14 for ii,jj in chosen):continue
                chosen.append((i,j))
                if len(chosen)>=limit:break
            for i,j in chosen:
                picks.append({'kind':kind,'label':LABELS[kind], 'lat':round(float(lat[i]),5),
                              'lon':round(float(lon[j]),5),'strength':round(float(arr[i,j]),4),
                              'unit':'°C/100 km' if kind=='sst_front' else '10⁻⁶ s⁻¹',
                              'search_radius_km':max(8,round(float(np.hypot(np.median(np.abs(np.diff(lat)))*111.195,np.median(np.abs(np.diff(lon)))*111.195*np.cos(np.deg2rad(lat[i])))),1)),
                              'interpretation':'Environmental feature, not a verified fishing hotspot'})
        # Up to 4 distinct kinds, top one per kind for an uncluttered bank summary.
        best=[next((p for p in picks if p['kind']==kind),None) for kind in KINDS]
        best=[p for p in best if p]
        by_bank[bank['key']]={'name':bank['name'],'bank_center':{'lat':bank['lat'],'lon':bank['lon']},
                               'search_radius_km':bank_radius_km,'features':best}
        for p in best:
            result.append({'type':'Feature','geometry':{'type':'Point','coordinates':[p['lon'],p['lat']]},
                           'properties':{'bank':bank['key'],**p}})
    return by_bank,result

def _history(path,by_bank,valid_date):
    path=Path(path)
    old=json.loads(path.read_text()) if path.exists() else {'banks':{}}
    if not isinstance(old,dict) or not isinstance(old.get('banks'),dict):
        raise ValueError('Invalid persisted feature history; refusing to overwrite')
    cutoff=(datetime.now(timezone.utc)-timedelta(days=30)).date().isoformat()
    recent_cutoff=(datetime.fromisoformat(valid_date).date()-timedelta(days=6)).isoformat()
    for key,bank in by_bank.items():
        rows=old['banks'].setdefault(key,[])
        if not isinstance(rows,list):raise ValueError('Invalid feature history rows')
        entry={'date':valid_date,'features':bank['features'],'model_version':VERSION}
        rows[:]=[r for r in rows if isinstance(r,dict) and r.get('date','')>=cutoff and r.get('date')!=valid_date]
        rows.append(entry);rows.sort(key=lambda r:r['date'])
        for p in bank['features']:
            # Persistence = independent distinct model-valid dates with nearby same-type features.
            matches=[]
            for r in rows:
                if r['date']==valid_date or r['date']<recent_cutoff:continue
                for other in r.get('features',[]):
                    if other.get('kind')!=p['kind']:continue
                    km=np.hypot((p['lat']-other['lat'])*111.195,(p['lon']-other['lon'])*111.195*np.cos(np.deg2rad(p['lat'])))
                    if km<=25:matches.append(r['date']);break
            p['historical_matching_dates']=len(set(matches))
            p['persistence']='building history' if len(rows)<3 else ('repeated feature' if len(set(matches))>=2 else 'not established')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(old,indent=2))
    return old

def build(out,banks,grid_path):
    out=Path(out)
    with np.load(grid_path) as data:
        lat=data['lats'];lon=data['lons'];sst=data['sst'];u=data['u'];v=data['v']
        sst_time=str(data['sst_time']);current_time=str(data['current_time'])
    fields=diagnostics(lat,lon,sst,u,v)
    by_bank,points=_candidates(fields,lat,lon,banks)
    valid_date=min(sst_time[:10],current_time[:10])
    _history(out/'feature-history.json',by_bank,valid_date)
    # Render native-resolution diagnostic overlays, not resampled fake precision.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    # Generate independently selectable maps from the same validated numerical grids.
    images={}
    boundary_lines=[]
    for selection,kinds in [('all',KINDS),('sst_front',('sst_front',)),
                            ('currents',('convergence','shear')),
                            ('eddy_candidate',('eddy_candidate',))]:
        fig=plt.figure(figsize=(13.5,9),dpi=125,facecolor='#061b33')
        ax=fig.add_subplot(111,projection=ccrs.PlateCarree())
        ax.set_extent([-79.5,-74.5,16,20],crs=ccrs.PlateCarree())
        ax.set_facecolor('#103a4e')
        ax.add_feature(cfeature.LAND,facecolor='#42474a',zorder=5)
        ax.coastlines(color='#b6c9d0',linewidth=.5,zorder=6)
        for kind in kinds:
            arr=fields[kind]
            finite=arr[np.isfinite(arr)]
            if len(finite)<8:continue
            level=np.percentile(finite,85)
            if level<=0:continue
            mask=np.where(np.isfinite(arr),arr,np.nan)
            if np.nanmax(mask)<=level:continue
            contour=ax.contour(lon,lat,mask,levels=[level],colors=[COLORS[kind]],linewidths=1.7,
                       transform=ccrs.PlateCarree(),zorder=4)
            if selection=='all':
                for segment in contour.allsegs[0][:120]:
                    if len(segment)<4: continue
                    step=max(1,int(np.ceil(len(segment)/150)))
                    coords=[[round(float(x),5),round(float(y),5)] for x,y in segment[::step]]
                    if len(coords)>1:
                        boundary_lines.append({'type':'Feature','geometry':{'type':'LineString','coordinates':coords},'properties':{'kind':kind,'label':LABELS[kind], 'strength_threshold':round(float(level),4),'unit':'°C/100 km' if kind=='sst_front' else '10⁻⁶ s⁻¹','sst_valid_utc':sst_time,'currents_valid_utc':current_time,'interpretation':'Model-derived boundary, not a fish location'}})
        for bank in banks:
            ax.scatter(bank['lon'],bank['lat'],marker='o',s=10,c='white',edgecolors='#092c39',zorder=8)
        ax.set_title('JAMAICA | OCEAN FRONTS & FISHING FEATURES',color='white',fontsize=15,pad=15)
        captions={'all':'Orange: SST fronts   Cyan: convergence   Pink: shear   Purple: rotation candidates',
                  'sst_front':'Orange: temperature fronts',
                  'currents':'Cyan: convergence   Pink: current shear',
                  'eddy_candidate':'Purple: possible rotation / eddy candidates'}
        fig.text(.5,.06,captions[selection],color='white',ha='center',fontsize=10)
        fig.text(.5,.035,'Experimental model diagnostics · Not fish locations · Not for navigation',color='#c9e0e6',ha='center',fontsize=9)
        filename='ocean-features.png' if selection=='all' else 'ocean-features-'+selection+'.png'
        fig.savefig(out/filename,facecolor=fig.get_facecolor(),bbox_inches='tight')
        plt.close(fig)
        images[selection]=filename
    for point in points:
        point['properties']['sst_valid_utc']=sst_time
        point['properties']['currents_valid_utc']=current_time
    geo={'type':'FeatureCollection','features':points+boundary_lines,'properties':{'model_version':VERSION,'sst_valid_utc':sst_time,'currents_valid_utc':current_time}}
    (out/'ocean-features.geojson').write_text(json.dumps(geo,indent=2))
    from shutil import copyfile
    copyfile(Path(__file__).with_name('ocean_features_interactive.html'),out/'ocean-features-interactive.html')
    copyfile(Path(__file__).with_name('jamaica-geography.svg'),out/'jamaica-geography.svg')
    return {'status':'available','image':'ocean-features.png','geojson':'ocean-features.geojson','images':images,
            'sst_valid_utc':sst_time,'currents_valid_utc':current_time,'banks':by_bank,
            'description':'Model-derived fronts, convergence, shear and rotation candidates. Not fish predictions.'}
