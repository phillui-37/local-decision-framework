import hashlib, json, os, pathlib, re, sys, uuid
from datetime import datetime, timezone

class EvidenceError(Exception):
 def __init__(self, code, **details): self.code=code; self.details=details

def _base():
 p=pathlib.Path(os.getenv('JEV_DATA_DIR',pathlib.Path.home()/'.local/share/jev')); p.mkdir(parents=True,mode=0o700,exist_ok=True); os.chmod(p,0o700); return p

def _append(path,row):
 path.parent.mkdir(parents=True,mode=0o700,exist_ok=True); os.chmod(path.parent,0o700); fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
 with os.fdopen(fd,'a',encoding='utf-8') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
 os.chmod(path,0o600)
def _digest(path):
 h=hashlib.sha256(); size=lines=0; last=b''
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(65536),b''): h.update(b); size+=len(b); lines+=b.count(b'\n'); last=b[-1:]
 if size and last!=b'\n': lines+=1
 return h.hexdigest(),size,lines
def _records():
 p=_base()/'sources.jsonl'
 return [json.loads(x) for x in p.read_text().splitlines() if x] if p.exists() else []
def register(path):
 rid=uuid.uuid4().hex[:12]
 if path=='-':
  p=_base()/'sources'/f'{rid}.txt'; p.parent.mkdir(mode=0o700,exist_ok=True); os.chmod(p.parent,0o700); fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as f:
   while True:
    b=sys.stdin.buffer.read(65536)
    if not b: break
    f.write(b)
  os.chmod(p,0o600); path=p
 p=pathlib.Path(path).expanduser().resolve()
 try: sha,size,n=_digest(p)
 except OSError: raise EvidenceError('source_unavailable')
 row={'ref_id':rid,'path':str(p),'sha256':sha,'bytes':size,'line_count':n,'registered_at':datetime.now(timezone.utc).isoformat()}; _append(_base()/'sources.jsonl',row); return row
def _source(ref):
 r=next((x for x in _records() if x['ref_id']==ref),None)
 if not r: raise EvidenceError('unknown_source')
 try: sha,_,_=_digest(r['path'])
 except OSError: raise EvidenceError('source_unavailable')
 if sha!=r['sha256']: raise EvidenceError('stale_source',registered_sha256=r['sha256'],current_sha256=sha)
 return r,pathlib.Path(r['path']).read_text(encoding='utf-8',errors='replace').splitlines()
MAVEN=re.compile(r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)')
GEN=re.compile(r'(\d+) (passed|failed|skipped)\b',re.I)
TIMED=re.compile(r'^\s*\d{2}:\d{2}:\d{2}\s+\[[^]]+\]\s+(ERROR|WARN)\s+\S+\s+-\s*(.*)',re.I)
def _level(line):
 m=TIMED.match(line)
 if m:return m.group(1).upper(),m.group(2)
 m=re.match(r'^\s*(?:\d{4}-\d\d-\d\d[T ][^ ]+\s+)?(?:ERROR|WARN)\s+|^\s*\[(ERROR|WARN)\]\s*|^\s*level=(error|warn)\b',line,re.I)
 if m:
  level=(m.group(1) or m.group(2) or line.strip().split()[0].strip('[]')).upper(); return level,line[m.end():]
 return None,''
def summarize(ref):
 r,ls=_source(ref); text='\n'.join(ls); totals=[MAVEN.search(x) for x in ls]; totals=[x for x in totals if x]
 counts={k:None for k in ('tests_total','passed','failed','errors','skipped','log_errors','log_warns')}; scope=[]
 if totals:
  rows=[tuple(map(int,x.groups())) for x in totals]; t=sum(x[0] for x in rows); f=sum(x[1] for x in rows); e=sum(x[2] for x in rows); s=sum(x[3] for x in rows)
  counts.update(tests_total=t,passed=t-f-e-s,failed=f,errors=e,skipped=s)
  if len(rows)>1: counts['totals_occurrences']=len(rows)
  scope.append(f'sum of all {len(rows)} Maven surefire totals lines')
 else:
  g={}
  for m in GEN.finditer(text):g[m.group(2).lower()]=int(m.group(1))
  if g: counts.update(passed=g.get('passed'),failed=g.get('failed'),skipped=g.get('skipped'),errors=0,tests_total=sum(g.values()));scope.append('generic passed/failed/skipped phrases')
 events=[]
 for i,line in enumerate(ls,1):
  level,msg=_level(line)
  if level in ('ERROR','WARN'):
   events.append((level,i,msg)); k='log_errors' if level=='ERROR' else 'log_warns'; counts[k]=(counts[k] or 0)+1
 counts['log_errors']=counts['log_errors'] or 0; counts['log_warns']=counts['log_warns'] or 0
 scope.append('ERROR/WARN header patterns run over the whole file; log counts are matches of these header patterns only; 0 matches does not establish the source contains no errors')
 first=next(({'name':m[:200] or 'ERROR','line':i} for lev,i,m in events if lev=='ERROR'),None)
 fail=bool((counts['failed'] or 0)>0 or (counts['errors'] or 0)>0 or counts['log_errors']>0 or re.search(r'BUILD FAILURE|status=FAIL',text,re.I))
 success_signal=bool(re.search(r'BUILD SUCCESS',text,re.I) or counts['tests_total'] is not None or counts['passed'] is not None)
 success=success_signal and counts['failed']==0 and counts['errors']==0 and counts['log_errors']==0
 status='fail' if fail else ('pass' if success else 'unknown')
 detection_scope='; '.join(scope) or 'checked Maven totals, generic test totals, ERROR/WARN header patterns, and build status patterns'
 return {'status':status,'counts':counts,'detection_scope':detection_scope,'detection_notes':'Log counts are matches of recognized ERROR/WARN header patterns only; 0 matches does not establish absence. Error detection is limited to recognized test totals, build status markers, and ERROR header patterns; unrecognized formats may not be detected.','first_failure':first,'display':{'shown_event_count':min(10,len(events)),'total_event_count':len(events),'complete':len(events)<=10},'preview_events':[{'line':i,'level':lev,'message':msg[:200]} for lev,i,msg in events[:10]],'recovery':{'ref_id':ref,'fetch_hint':f'ldf source fetch {ref} --errors all'},'source':{'sha256':r['sha256'],'line_count':r['line_count'],'bytes':r['bytes']}}
def fetch(ref,lines=None,errors=None,pattern=None,context=2):
 r,src=_source(ref); c=max(0,min(int(context),20)); chosen=[]; truncated=False; total=None
 if lines:
  m=re.fullmatch(r'(\d+):(\d+)',lines)
  if not m:raise EvidenceError('invalid_lines')
  a,b=map(int,m.groups())
  if a<1 or b<a or b-a+1>200:raise EvidenceError('fetch_limit_exceeded')
  chosen=list(range(a,min(b,len(src))+1)); truncated=b>len(src)
 elif errors:
  hits=[i for i,x in enumerate(src,1) if _level(x)[0]=='ERROR']; total=len(hits); m=re.search(r'(\d+)',errors); target=hits if errors=='all' else hits[:int(m.group(1)) if m else 20]
  if len(target)>20:raise EvidenceError('fetch_limit_exceeded')
  truncated=len(target)<total
  chosen=sorted({n for i in target for n in range(max(1,i-c),min(len(src),i+c)+1)})
 elif pattern is not None:
  hits=[i for i,x in enumerate(src,1) if pattern in x]; total=len(hits)
  if len(hits)>50:raise EvidenceError('fetch_limit_exceeded')
  truncated=False
  chosen=sorted({n for i in hits for n in range(max(1,i-c),min(len(src),i+c)+1)})
 else:raise EvidenceError('fetch_mode_required')
 if len(chosen)>200:raise EvidenceError('fetch_limit_exceeded')
 out=[{'line':i,'text':src[i-1]} for i in chosen]
 if sum(len(x['text'].encode())+16 for x in out)>32768:raise EvidenceError('fetch_limit_exceeded')
 result={'ref_id':ref,'lines':out,'truncated':{'lines':truncated,'bytes':False}}
 if errors: result['total_errors_in_source']=total
 if pattern is not None: result['total_matches_in_source']=total
 return result
