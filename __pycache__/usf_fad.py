"""Retrieve published USF Jamaica FAD images, without creating synthetic observations.

USF HTML is parsed at runtime. Image URLs are intentionally not guessed.
If their public HTML changes, the generator reports unavailable data.
"""
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

USF_PAGE = 'https://optics.marine.usf.edu/cgi-bin/optics_data?roi=JAMAICA&comp=1'
AGENT = 'JamaicaMarineWeather/3.8.11 (public imagery attribution; no bulk crawling)'

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.images=[]; self._anchor=None
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='a': self._anchor={'href':a.get('href',''),'text':'','title':a.get('title','')}
        if tag=='img': self.images.append({'src':a.get('src',''),'alt':a.get('alt',''),'title':a.get('title','')})
    def handle_data(self, data):
        if self._anchor: self._anchor['text']+=data
    def handle_endtag(self, tag):
        if tag=='a' and self._anchor:
            self.links.append(self._anchor);self._anchor=None

def fetch(url, limit=12000000):
    req=Request(url,headers={'User-Agent':AGENT})
    with urlopen(req,timeout=24) as response:
        raw=response.read(limit+1)
        if len(raw)>limit: raise ValueError('USF response exceeds allowed size')
        return raw, response.headers.get('Content-Type','')

def observation_date(filename):
    # USF naming example c20262802026280.1KM.JAMAICA.1DAY.L3D.FAD.png
    m=re.search(r'c(20\d{2})(\d{3})(20\d{2})(\d{3})',filename,re.I)
    if not m:return None
    try:
        start=datetime(int(m[1]),1,1,tzinfo=timezone.utc)+timedelta(days=int(m[2])-1)
        end=datetime(int(m[3]),1,1,tzinfo=timezone.utc)+timedelta(days=int(m[4])-1)
        if end<start or end>datetime.now(timezone.utc)+timedelta(days=1):return None
        return start.date().isoformat(),end.date().isoformat()
    except ValueError:return None

def candidates(html, base):
    parser=Links();parser.feed(html)
    results=[]
    for entry in parser.links+parser.images:
        href=entry.get('href') or entry.get('src') or ''
        context=' '.join(str(x) for x in entry.values())
        if not re.search(r'FAD',context,re.I):continue
        for token in [href]+re.findall(r'[\w./%-]*JAMAICA[\w./%-]*FAD\.(?:png|jpg|jpeg)',context,re.I):
            if not token:continue
            full=urljoin(base,token.replace('&amp;','&'))
            if urlparse(full).hostname != 'optics.marine.usf.edu':continue
            results.append((full,context))
    return results

def generate_fad(out):
    """Returns metadata for both products; does not break ocean map generation."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    result={'label':'Sargassum / Possible Weedlines','source':'University of South Florida',
            'source_page':USF_PAGE,'views':{},'error':None}
    try:
        html,ctype=fetch(USF_PAGE,2000000)
        if b'<html' not in html[:10000].lower() and 'html' not in ctype.lower():
            raise ValueError('USF did not return an HTML image listing')
        listing=candidates(html.decode('utf-8','replace'),USF_PAGE)
    except Exception as exc:
        result['error']='Satellite imagery could not be refreshed'
        print('USF listing unavailable:',type(exc).__name__,str(exc)[:200]);listing=[]
    for key, tokens in [('1day',['1DAY']),('7day',['7DAY'])]:
        valid=[]
        for url,context in listing:
            # Do not accidentally use 7-day images as daily observations.
            if not all(t in context.upper() for t in tokens):continue
            if key=='1day' and '7DAY' in url.upper():continue
            # Only use direct PNG/JPEG files. A CGI listing is not an image.
            if not re.search(r'\.(?:png|jpe?g)(?:\?|$)',url,re.I):continue
            dates=observation_date(url)
            if not dates:continue
            valid.append((dates[1],dates[0],url))
        valid.sort(reverse=True)
        if valid:
            end,start,url=valid[0]
            try:
                raw,ctype=fetch(url)
                from PIL import Image
                from io import BytesIO
                with Image.open(BytesIO(raw)) as im:
                    im.verify()
                if not (raw.startswith(b'\x89PNG') or raw.startswith(b'\xff\xd8')):
                    raise ValueError('Unexpected image encoding')
                suffix='.png' if raw.startswith(b'\x89PNG') else '.jpg'
                filename='sargassum-fad-'+key+suffix
                (out/filename).write_bytes(raw)
                result['views'][key]={'image':filename,'observation_start':start,
                    'observation_end':end,'observation_date':end,'status':'available'}
                print('USF FAD',key,end,filename)
                continue
            except Exception as exc:
                print('USF image unavailable:',key,type(exc).__name__,str(exc)[:160])
        # No misleading dates: only reuse a previous image with its stored metadata.
        old_path=out/'sargassum.json'
        try:
            previous=json.loads(old_path.read_text())
            old=previous.get('views',{}).get(key,{})
            img=old.get('image','')
            if img and Path(img).name==img and (out/img).is_file():
                result['views'][key]={**old,'status':'previous_observation'}
                continue
        except (OSError,ValueError,TypeError):pass
        result['views'][key]={'status':'unavailable'}
    (out/'sargassum.json').write_text(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    generate_fad(Path(__file__).parent/'site')
