"""Bank-oriented environmental context; never a fish probability model."""
import json
import numpy as np
from scipy.ndimage import gaussian_filter

METHODS = {
 'trolling': {'label':'Offshore trolling','species':'Mahi-mahi, tuna, wahoo, marlin and mackerel','description':'Review thermal boundaries, currents and floating structure; not a catch forecast.'},
 'jigging': {'label':'Vertical jigging','species':'Jacks, tuna, grouper, snapper, wahoo and mackerel','description':'Review bank structure and current speed; subsurface conditions are not measured here.'},
 'bottom': {'label':'Bottom fishing','species':'Snapper, grouper and jacks','description':'Review known bank positions; verified bottom habitat and depth are not included in this assessment.'},
}

def build(out, banks):
    """Use saved *numerical* grids from existing current/SST map generation."""
    f=out/'opportunities-grids.npz'
    if not f.exists():
        return {'status':'unavailable','banks':[],'methods':METHODS}
    with np.load(f) as d:
        lats=d['lats']; lons=d['lons']; u=d['u']; v=d['v']; sst=d['sst']; current_time=str(d['current_time']); sst_time=str(d['sst_time'])
    if u.shape!=sst.shape or v.shape!=sst.shape or u.shape!=(len(lats),len(lons)):
        return {'status':'unavailable','banks':[],'methods':METHODS,'note':'Current and SST grids do not align'}
    speed=np.hypot(u,v)*1.943844
    # Only descriptive gradients, not predictions. Exclude invalid/land pixels.
    sst_valid=np.isfinite(sst)
    sst_smooth=gaussian_filter(np.where(sst_valid,sst,0),1)/np.maximum(gaussian_filter(sst_valid.astype(float),1),1e-6)
    gy,gx=np.gradient(sst_smooth,float(np.nanmedian(np.diff(lats)))*111.0,float(np.nanmedian(np.diff(lons)))*106.0)
    grad=np.hypot(gx,gy)
    threshold=float(np.nanpercentile(grad[sst_valid],75)) if sst_valid.any() else np.nan
    rows=[]
    for b in banks:
        x=int(np.argmin(abs(lons-float(b['lon']))));y=int(np.argmin(abs(lats-float(b['lat']))))
        y0,y1=max(0,y-2),min(len(lats),y+3);x0,x1=max(0,x-2),min(len(lons),x+3)
        local_sst=sst[y0:y1,x0:x1];local_speed=speed[y0:y1,x0:x1];local_grad=grad[y0:y1,x0:x1]
        def med(a):
            z=a[np.isfinite(a)];return round(float(np.median(z)),2) if z.size else None
        g=med(local_grad)
        rows.append({'key':b['key'],'name':b['name'],'lat':b['lat'],'lon':b['lon'],
          'sst_c':med(local_sst),'current_knots':med(local_speed),
          'thermal_boundary_nearby':bool(g is not None and np.isfinite(threshold) and g>=threshold),
          'chlorophyll':'Not assessed at bank','weedlines':'Check USF satellite view',
          'depth':'Not assessed','current_time_utc':current_time,'sst_time_utc':sst_time})
    return {'status':'available','banks':rows,'methods':METHODS,'note':'Model grid values are approximate. Front indicator compares local SST gradient to the regional upper quartile; not a species suitability score.'}

def render_map(out,banks):
    """Simple contextual SST/current map, independent of pelagic composite."""
    f=out/'opportunities-grids.npz'
    if not f.exists():return None
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    with np.load(f) as d:
        lat=d['lats'];lon=d['lons'];sst=d['sst'];u=d['u'];v=d['v']
    fig=plt.figure(figsize=(13.5,9),dpi=145,facecolor='#061b33')
    ax=fig.add_subplot(111,projection=ccrs.PlateCarree())
    ax.set_extent([-79.5,-74.5,16,20])
    im=ax.pcolormesh(lon,lat,sst,shading='auto',cmap='turbo',transform=ccrs.PlateCarree())
    stride=max(1,int(max(len(lat),len(lon))/22))
    ax.quiver(lon[::stride],lat[::stride],u[::stride,::stride],v[::stride,::stride],color='white',alpha=.8,scale=12,width=.002,transform=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND.with_scale('10m'),facecolor='white',zorder=4)
    ax.coastlines(resolution='10m',color='#28455e',zorder=5)
    for b in banks:
        ax.scatter([b['lon']],[b['lat']],s=20,edgecolors='white',facecolors='#ffcc33',transform=ccrs.PlateCarree(),zorder=6)
        ax.annotate(b['name'],(b['lon'],b['lat']),xytext=(5,4),textcoords='offset points',color='white',fontsize=7,zorder=7)
    ax.set_title('JAMAICA | FISHING OPPORTUNITIES\nSST and surface currents',color='white',fontsize=14,pad=18)
    cb=fig.colorbar(im,ax=ax,orientation='horizontal',pad=.035,shrink=.65);cb.set_label('Sea surface temperature (°C)',color='white');cb.ax.tick_params(colors='white')
    fig.text(.5,.02,'Environmental context only. Not a fish forecast or navigation chart.',ha='center',color='white',fontsize=9)
    name='fishing-opportunities.png';fig.savefig(out/name,bbox_inches='tight',facecolor=fig.get_facecolor());plt.close(fig)
    return name
