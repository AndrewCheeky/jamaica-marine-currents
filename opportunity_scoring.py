"""Experimental, transparent environmental suitability indices, NOT catch probabilities.
No species-specific model has been calibrated against catch/effort observations.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter

# Heuristic weights sum to 100. A score is suppressed when less than 60% of
# relevant inputs are available; missing indicators are never assigned zero.
WEIGHTS = {
 'mahi': {'sst':25,'thermal_front':20,'chlorophyll':15,'chl_front':15,'current':15,'depth':10},
 'tuna': {'sst':20,'thermal_front':20,'chlorophyll':20,'chl_front':20,'current':15,'depth':5},
 'wahoo': {'sst':20,'thermal_front':20,'chlorophyll':10,'chl_front':10,'current':20,'depth':20},
 'marlin': {'sst':20,'thermal_front':25,'chlorophyll':10,'chl_front':15,'current':20,'depth':10},
 'snapper': {'sst':5,'thermal_front':5,'chlorophyll':10,'chl_front':5,'current':15,'depth':60},
 'jacks': {'sst':10,'thermal_front':10,'chlorophyll':10,'chl_front':10,'current':25,'depth':35},
}
SPECIES = {
 'mahi': {'label':'Mahi-mahi','method':'trolling'},
 'tuna': {'label':'Tuna','method':'trolling'},
 'wahoo': {'label':'Wahoo','method':'trolling'},
 'marlin': {'label':'Marlin','method':'trolling'},
 'snapper': {'label':'Snapper','method':'bottom'},
 'jacks': {'label':'Jacks','method':'jigging'},
}
METHODS = {'trolling':'Offshore trolling','jigging':'Vertical jigging','bottom':'Bottom fishing'}

def _range_score(value,low,ideal_lo,ideal_hi,high):
    if value is None or not np.isfinite(value): return None
    if value<=low or value>=high: return 0.
    if ideal_lo<=value<=ideal_hi: return 100.
    if value<ideal_lo: return round(100*(value-low)/(ideal_lo-low))
    return round(100*(high-value)/(high-ideal_hi))

def _median_near(lat,lon,values,blat,blon,radius=2):
    iy=int(np.argmin(abs(lat-blat)));ix=int(np.argmin(abs(lon-blon)))
    window=values[max(0,iy-radius):iy+radius+1,max(0,ix-radius):ix+radius+1]
    finite=window[np.isfinite(window)]
    return float(np.median(finite)) if finite.size else None

def _grad(lat,lon,values):
    good=np.isfinite(values)
    if not good.any():return np.full_like(values,np.nan,dtype=float)
    smooth=gaussian_filter(np.where(good,values,0.),1)/np.maximum(gaussian_filter(good.astype(float),1),1e-8)
    dy=max(0.01,abs(float(np.nanmedian(np.diff(lat))))*111)
    dx=max(0.01,abs(float(np.nanmedian(np.diff(lon))))*111*np.cos(np.deg2rad(float(np.mean(lat)))))
    gy,gx=np.gradient(smooth,dy,dx)
    g=np.hypot(gx,gy);g[~good]=np.nan
    return g

def _fetch_chl(bounds,user,password,dataset_id):
    import copernicusmarine
    w,e,s,n=bounds;now=datetime.now(timezone.utc)
    ds=copernicusmarine.open_dataset(dataset_id=dataset_id,variables=['CHL'],minimum_longitude=w,maximum_longitude=e,
        minimum_latitude=s,maximum_latitude=n,start_datetime=(now-timedelta(days=9)).strftime('%Y-%m-%dT00:00:00'),
        end_datetime=now.strftime('%Y-%m-%dT23:59:59'),username=user,password=password)
    field=ds['CHL'].isel(time=-1).squeeze(drop=True)
    lat=np.asarray(field['latitude' if 'latitude' in field.coords else 'lat'].values,float)
    lon=np.asarray(field['longitude' if 'longitude' in field.coords else 'lon'].values,float)
    vals=np.asarray(field.values,float)
    date=np.datetime_as_string(np.asarray(ds.time.values)[-1],unit='D')
    if vals.shape!=(len(lat),len(lon)):raise ValueError('Invalid chlorophyll grid')
    vals[(vals<=0)|(~np.isfinite(vals))]=np.nan
    return lat,lon,vals,date

def enrich(out,banks,bounds,username,password,chl_dataset,grid_path):
    """Add numeric chlorophyll and GEBCO depth to existing bank rows; fail independently."""
    out=Path(out)
    chl=None;depth=None;notes=[]
    try:
        chl=_fetch_chl(bounds,username,password,chl_dataset)
    except Exception as ex:
        notes.append('Chlorophyll data unavailable: '+str(ex)[:160])
    try:
        import xarray as xr
        if Path(grid_path).is_file():
            with xr.open_dataset(grid_path) as ds:
                a=ds['elevation'];lat=np.asarray(a.lat.values,float);lon=np.asarray(a.lon.values,float)
                vals=np.asarray(a.values,float);vals[vals>=0]=np.nan
                depth=(lat,lon,-vals)
        else: notes.append('Bathymetry grid unavailable')
    except Exception as ex:notes.append('Bathymetry unavailable: '+str(ex)[:160])
    if chl is not None:
        clat,clon,cvals,cdate=chl
        cgrad=_grad(clat,clon,np.log10(cvals))
        valid=cgrad[np.isfinite(cgrad)]
        cfront_threshold=float(np.percentile(valid,75)) if len(valid)>10 else None
    if depth is not None:
        dlat,dlon,dvals=depth
    return {'chl':chl,'depth':depth,'notes':notes,'chl_front_threshold':cfront_threshold if chl is not None else None}

def add_scores(info,extra):
    chl=extra['chl'];depth=extra['depth']
    for b in info.get('banks',[]):
        if chl is not None:
            lat,lon,v,date=chl
            b['chlorophyll_mg_m3']=_round(_median_near(lat,lon,v,b['lat'],b['lon']))
            # Gradient computed on observed concentration field; not an algae/fish density measure.
            grad=_grad(lat,lon,np.log10(v))
            g=_median_near(lat,lon,grad,b['lat'],b['lon'])
            threshold=extra['chl_front_threshold']
            b['chlorophyll_front_nearby']=bool(g is not None and threshold is not None and g>=threshold)
            b['chlorophyll_date']=date
        else:
            b['chlorophyll_mg_m3']=None;b['chlorophyll_front_nearby']=None;b['chlorophyll_date']=None
        if depth is not None:
            lat,lon,v=depth
            b['depth_m']=_round(_median_near(lat,lon,v,b['lat'],b['lon'],radius=3),0)
        else:b['depth_m']=None
        b['species_scores']={}
        for species,weights in WEIGHTS.items():
            sst=b.get('sst_c');cur=b.get('current_knots');dep=b.get('depth_m');c=b.get('chlorophyll_mg_m3')
            # Broad demonstration heuristics; NOT empirically validated habitat thresholds.
            factor={
                'sst':_range_score(sst,20,26,30,34),
                'thermal_front':(85 if b.get('thermal_boundary_nearby') else 35) if sst is not None else None,
                'chlorophyll':_range_score(c,0.015,0.08,0.6,3) if c is not None else None,
                'chl_front':(85 if b['chlorophyll_front_nearby'] else 35) if b['chlorophyll_front_nearby'] is not None else None,
                'current':_range_score(cur,0,0.3,1.8,4) if cur is not None else None,
                'depth':_depth_score(dep,species),
            }
            available=sum(w for k,w in weights.items() if factor[k] is not None)
            score=round(sum(w*factor[k] for k,w in weights.items() if factor[k] is not None)/available) if available>=60 else None
            b['species_scores'][species]={'score':score,'data_completeness_pct':available,'factors':{k:{'score':factor[k],'weight':w} for k,w in weights.items()},'method':SPECIES[species]['method'],'label':SPECIES[species]['label']}
        b['method_scores']={}
        for method in METHODS:
            valid=[v['score'] for v in b['species_scores'].values() if v['method']==method and v['score'] is not None]
            b['method_scores'][method]=round(max(valid)) if valid else None
        all_valid=[(k,v) for k,v in b['species_scores'].items() if v['score'] is not None]
        best=max(all_valid,key=lambda pair:pair[1]['score']) if all_valid else None
        b['overall_score']=best[1]['score'] if best else None
        b['best_supported_species']=SPECIES[best[0]]['label'] if best else None
        b['best_method']=METHODS[SPECIES[best[0]]['method']] if best else None
    info['scoring']={'type':'experimental_environmental_opportunity_index','is_catch_probability':False,'calibrated':False,
        'description':'Heuristic environmental suitability only. Not probability of catching fish. Species thresholds and weights are not validated for Jamaica.',
        'minimum_data_completeness_pct':60,'notes':extra['notes']}
    return info

def _depth_score(dep,species):
    if dep is None:return None
    if species=='snapper':return _range_score(dep,10,80,350,1200)
    if species=='jacks':return _range_score(dep,10,80,600,2500)
    return _range_score(dep,20,150,1800,5500)

def _round(v,nd=2):return round(v,nd) if v is not None and np.isfinite(v) else None
