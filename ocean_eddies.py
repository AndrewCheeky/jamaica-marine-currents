"""Optional observational sea-level anomaly map. No fabricated eddy centers."""
import os
from datetime import datetime,timedelta,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import copernicusmarine

def generate(out,banks,bounds,username,password):
    west,east,south,north=bounds
    dataset=os.getenv('COPERNICUS_EDDY_DATASET_ID','cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D')
    end=datetime.now(timezone.utc);start=end-timedelta(days=8)
    try:
        ds=copernicusmarine.open_dataset(dataset_id=dataset,variables=['sla','ugos','vgos'],
            minimum_longitude=west,maximum_longitude=east,minimum_latitude=south,maximum_latitude=north,
            start_datetime=start.strftime('%Y-%m-%dT%H:%M:%S'),end_datetime=end.strftime('%Y-%m-%dT%H:%M:%S'),
            username=username,password=password)
        if ds.sizes.get('time',0)==0:raise ValueError('No sea-level observation times')
        ds=ds.isel(time=-1)
        z=np.asarray(ds['sla'].squeeze().values,dtype=float)
        u=np.asarray(ds['ugos'].squeeze().values,dtype=float);v=np.asarray(ds['vgos'].squeeze().values,dtype=float)
        la=np.asarray(ds['latitude'].values);lo=np.asarray(ds['longitude'].values)
        if z.shape!=(len(la),len(lo)) or not np.isfinite(z).any():raise ValueError('Invalid sea-level grid')
        fig=plt.figure(figsize=(13.5,9),dpi=145,facecolor='#061b33')
        ax=fig.add_subplot(111,projection=ccrs.PlateCarree());ax.set_extent([west,east,south,north])
        vmax=max(.05,float(np.nanpercentile(abs(z),98)))
        im=ax.pcolormesh(lo,la,z,cmap='RdBu_r',vmin=-vmax,vmax=vmax,shading='auto',transform=ccrs.PlateCarree())
        # Arrows are observed geostrophic flow; closed SLA patches alone are not verified eddies.
        stride=max(1,int(max(len(la),len(lo))/22))
        ax.quiver(lo[::stride],la[::stride],u[::stride,::stride],v[::stride,::stride],color='white',alpha=.8,scale=12,width=.0023,transform=ccrs.PlateCarree())
        ax.add_feature(cfeature.LAND.with_scale('10m'),facecolor='white',zorder=4);ax.coastlines(resolution='10m',color='#28455e',linewidth=.7,zorder=5)
        for b in banks:
            ax.plot(b['lon'],b['lat'],marker='o',markersize=3.5,color='#ffd166',transform=ccrs.PlateCarree(),zorder=6)
            ax.annotate(b['name'],(b['lon'],b['lat']),xytext=(5,4),textcoords='offset points',color='white',fontsize=6.4,zorder=7,path_effects=[])
        stamp=str(np.datetime_as_string(ds['time'].values,unit='D'))
        ax.set_title('JAMAICA | OCEAN EDDY CONTEXT\nSatellite sea-level anomaly & geostrophic currents | '+stamp+' UTC',color='white',fontsize=14,pad=18)
        cb=fig.colorbar(im,ax=ax,orientation='horizontal',pad=.035,shrink=.65);cb.set_label('Sea-level anomaly (metres) · blue lower / red higher',color='white');cb.ax.tick_params(colors='white')
        fig.text(.5,.02,'Candidate eddy context, not automated verified eddy detection. Not for navigation.',ha='center',color='white',fontsize=9)
        filename='ocean-eddies.png';fig.savefig(out/filename,bbox_inches='tight',facecolor=fig.get_facecolor());plt.close(fig)
        return {'status':'available','image':filename,'observation_date':stamp,'dataset':dataset,'description':'Satellite sea-level anomaly and geostrophic currents. Closed anomalies are not independently verified eddies.'}
    except Exception as exc:
        print('WARNING: ocean eddies unavailable:',type(exc).__name__,str(exc)[:450])
        return {'status':'unavailable','image':None,'description':'Recent satellite sea-level observations are temporarily unavailable. Other maps remain accessible.'}
