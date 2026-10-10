"""Pelagic indicators from independent observed/model oceanographic grids.
Only display contours when real, recent inputs are available. No fish predictions.
"""
import os
import numpy as np
from scipy.ndimage import gaussian_filter, binary_erosion, label
from scipy.interpolate import RegularGridInterpolator


def _gradient(values, lat, lon, sigma=1.4):
    good=np.isfinite(values)
    w=gaussian_filter(good.astype(float),sigma)
    smooth=gaussian_filter(np.where(good,values,0),sigma)/np.maximum(w,1e-8)
    smooth[w<.85]=np.nan
    dx=np.gradient(lon)[None,:]*111.2*np.cos(np.deg2rad(lat[:,None]))
    dy=np.gradient(lat)[:,None]*111.2
    strength=np.hypot(np.gradient(smooth,axis=1)/dx,np.gradient(smooth,axis=0)/dy)
    strength[~binary_erosion(good,iterations=2)]=np.nan
    return strength


def _mask_top(gradient, q=.94, min_pixels=9):
    valid=gradient[np.isfinite(gradient)&(gradient>0)]
    if len(valid)<15:return np.full_like(gradient,np.nan)
    threshold=np.quantile(valid,q)
    hits=np.isfinite(gradient)&(gradient>=threshold)
    groups,n=label(hits)
    counts=np.bincount(groups.ravel())
    hits &= (groups>0)&(counts[groups]>=min_pixels)
    return np.where(hits,gradient,np.nan)


def _onto(src_lon,src_lat,src_values,target_lon,target_lat):
    # Ensure model and satellite grids are not mistaken for identical resolutions.
    if src_lat[0]>src_lat[-1]:src_lat,src_values=src_lat[::-1],src_values[::-1]
    if src_lon[0]>src_lon[-1]:src_lon,src_values=src_lon[::-1],src_values[:,::-1]
    fn=RegularGridInterpolator((src_lat,src_lon),src_values,bounds_error=False,fill_value=np.nan)
    xx,yy=np.meshgrid(target_lon,target_lat)
    return fn(np.column_stack([yy.ravel(),xx.ravel()])).reshape(xx.shape)


def indicators(bounds,username,password,chl_lon,chl_lat,chl_date,fetch,grid):
    result={'sst_date':None,'current_date':None,'sst_fronts':None,'convergence':None,'overlap':None,'notes':[]}
    sst_dataset=os.getenv('COPERNICUS_SST_DATASET_ID','cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m')
    cur_dataset=os.getenv('COPERNICUS_DATASET_ID','cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i')
    try:
        lo,la,values,date=grid(fetch(sst_dataset,['thetao'],bounds,username,password,days=4),'thetao')
        if values.shape!=(len(la),len(lo)):raise ValueError('Unexpected SST dimensions')
        # Avoid misleading overlay from stale forecast compared to observed chlorophyll.
        if abs((np.datetime64(date)-np.datetime64(chl_date)).astype('timedelta64[D]').astype(int))>4:
            raise ValueError('SST date more than four days from chlorophyll observation')
        g=_gradient(values,la,lo)
        front=_mask_top(g,.94,min_pixels=5)
        if np.isfinite(front).sum()<5:raise ValueError('No coherent thermal fronts')
        result['sst_fronts']=(lo,la,front)
        result['sst_date']=date
    except Exception as exc:
        result['notes'].append('SST fronts unavailable')
        print('WARNING: pelagic SST front unavailable:',str(exc)[:200])
    try:
        ds=fetch(cur_dataset,['uo','vo'],bounds,username,password,days=3)
        lo,la,u,date=grid(ds,'uo')
        _,_,v,_=grid(ds,'vo')
        if u.shape!=v.shape or u.shape!=(len(la),len(lo)):raise ValueError('Unexpected current dimensions')
        if abs((np.datetime64(date)-np.datetime64(chl_date)).astype('timedelta64[D]').astype(int))>4:
            raise ValueError('Current model date more than four days from chlorophyll observation')
        # Horizontal convergence proxy -div(u,v) in s^-1, with metric grid spacing.
        valid=np.isfinite(u)&np.isfinite(v)
        if valid.sum()<20:raise ValueError('Insufficient valid surface currents')
        sigma=1.2
        weight=gaussian_filter(valid.astype(float),sigma)
        us=gaussian_filter(np.where(valid,u,0),sigma)/np.maximum(weight,1e-8)
        vs=gaussian_filter(np.where(valid,v,0),sigma)/np.maximum(weight,1e-8)
        dx=np.gradient(lo)[None,:]*111200*np.cos(np.deg2rad(la[:,None]))
        dy=np.gradient(la)[:,None]*111200
        convergence=-(np.gradient(us,axis=1)/dx+np.gradient(vs,axis=0)/dy)
        convergence[~binary_erosion(valid,iterations=2)]=np.nan
        strong=_mask_top(np.where(convergence>0,convergence,np.nan),.90,min_pixels=3)
        if np.isfinite(strong).sum()<3:raise ValueError('No coherent convergence regions')
        result['convergence']=(lo,la,strong)
        result['current_date']=date
    except Exception as exc:
        result['notes'].append('Current convergence unavailable')
        print('WARNING: pelagic convergence unavailable:',str(exc)[:200])
    return result
