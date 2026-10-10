from pathlib import Path
p=Path('generate.py'); s=p.read_text(); start=s.index('<script>(async()=>{'); end=s.index('</script></body></html>',start)
js=r'''<script>(async()=>{
const status=document.querySelector('#time'),map=document.querySelector('#map'),layer=document.querySelector('#layer'),msg=document.querySelector('#message'),fadControls=document.querySelector('#fad-controls'),fadPeriod=document.querySelector('#fad-period'),fadNote=document.querySelector('#fad-note'),forecastControls=document.querySelector('#forecast-controls');
let data=null, fad=null, period='current';
const fmt=(iso)=>{if(!iso)return 'Unknown';const d=new Date(iso+'T12:00:00Z');return Number.isNaN(d.getTime())?iso:new Intl.DateTimeFormat('en-JM',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(d)};
function displayImage(src,alt){map.hidden=false;map.setAttribute('aria-busy','true');const next=new Image();next.onload=()=>{map.src=next.src;map.alt=alt;map.removeAttribute('aria-busy')};next.onerror=()=>{map.hidden=true;map.removeAttribute('aria-busy');msg.textContent='Satellite image could not be loaded. Please try again later.'};next.src=src;}
function show(){const isFad=layer.value==='sargassum';fadControls.hidden=!isFad;forecastControls.hidden=isFad;
if(isFad){const view=fad?.views?.[fadPeriod.value];fadNote.textContent='Source: University of South Florida (USF). Satellite observations, not a weedline forecast.';
if(!view?.image){map.hidden=true;status.textContent='Satellite imagery is currently unavailable.';msg.textContent='No verified '+(fadPeriod.value==='1day'?'daily':'seven-day')+' observation is available. Other marine maps remain available.';return;}
const range=view.observation_start&&view.observation_start!==view.observation_end?fmt(view.observation_start)+' to '+fmt(view.observation_end):fmt(view.observation_end||view.observation_date);
status.textContent=(fadPeriod.value==='1day'?'FAD 1DAY':'FAD 7DAY MEAN')+' · Satellite observations: '+range;
msg.textContent=view.status==='previous_observation'?'Showing the last successfully retrieved satellite observation. Floating algae may have moved.':'';
displayImage(view.image+'?observed='+encodeURIComponent(view.observation_end||''),'USF Jamaica floating algae density satellite observations, '+range);return;}
const item=data?.layers?.[layer.value],f=item?.forecasts?.find(x=>x.key===period);
document.querySelectorAll('button[data-period]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.period===period)));
if(!f){map.hidden=true;status.textContent='This overlay is currently unavailable.';msg.textContent=item?.error||'Try a different overlay.';return;}
msg.textContent='';status.textContent=f.label+' · '+item.label+' · Model time: '+f.model_time_jamaica;displayImage(f.image,f.label+' '+item.label+' map of Jamaica');}
layer.addEventListener('change',show);fadPeriod.addEventListener('change',show);document.querySelectorAll('button[data-period]').forEach(b=>b.addEventListener('click',()=>{period=b.dataset.period;show()}));
try{const r=await fetch('forecast.json',{cache:'no-store'});if(!r.ok)throw Error('Forecast metadata unavailable');data=await r.json();const updated=document.querySelector('#updated');if(data.generated_utc){updated.textContent='Last updated: '+new Intl.DateTimeFormat('en-JM',{timeZone:'America/Jamaica',weekday:'short',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:true}).format(new Date(data.generated_utc))+' (Jamaica time)';}else updated.textContent='Last updated: unavailable';fad=data.sargassum||null;
if(!fad){try{const fr=await fetch('sargassum.json',{cache:'no-store'});if(fr.ok)fad=await fr.json()}catch(e){}}
show();}catch(e){status.textContent='Forecast metadata unavailable; displaying last published current map.';document.querySelector('#updated').textContent='Last updated: unavailable';msg.textContent='';}
})();'''
s=s[:start]+js+s[end:];s=s.replace("'version': '3.8.11'", "'version': '3.8.12'")
s=s.replace('const next=new Image();next.onload=', 'const next=new Image();next.onload=')
p.write_text(s)
