import argparse, json, os, sys, uuid
from datetime import datetime, timezone
from .core import judge, judge_claims, replay, Rejected, _paths, _append, _rows, _timeout, _env
from . import evidence

def _emit(x): print(json.dumps(x,ensure_ascii=False))
def _issues(): return [r for r in _rows(_paths()[1]) if r.get('record_type')=='issue']
def _issue_events(): return [r for r in _rows(_paths()[1]) if r.get('record_type')=='transition']
def main():
 p=argparse.ArgumentParser(prog='ldf'); sub=p.add_subparsers(dest='command')
 doctor=sub.add_parser('doctor'); doctor.add_argument('--probe',action='store_true')
 receipts=sub.add_parser('receipts'); rs=receipts.add_subparsers(dest='receipts_command'); rs.add_parser('list'); sh=rs.add_parser('show'); sh.add_argument('request_id'); rex=rs.add_parser('export'); rex.add_argument('--format',choices=('json','jsonl'),default='json')
 judgep=sub.add_parser('judge'); judgep.add_argument('--capture',action='store_true',help='Capture normalized input and rendered request locally')
 batp=sub.add_parser('judge-claims'); batp.add_argument('--capture',action='store_true',help='Capture normalized input and rendered request locally')
 fb=sub.add_parser('feedback'); fs=fb.add_subparsers(dest='feedback_command'); fs.add_parser('list'); ex=fs.add_parser('export'); ex.add_argument('--format',choices=('json','jsonl'),default='json')
 add=fs.add_parser('add'); add.add_argument('request_id'); add.add_argument('expected',choices=('supported','contradicted','insufficient_evidence')); add.add_argument('--kind',choices=('agent-test','human'),default='agent-test'); add.add_argument('--observed-verdict',choices=('supported','contradicted','insufficient_evidence')); add.add_argument('--reason',default='')
 issue=sub.add_parser('issue'); ix=issue.add_subparsers(dest='issue_command'); ix.add_parser('list'); ish=ix.add_parser('show'); ish.add_argument('issue_id'); upd=ix.add_parser('update'); upd.add_argument('issue_id'); upd.add_argument('status',choices=('confirmed','fixed','regression_tested','open')); upd.add_argument('--kind',choices=('agent-test','human'),default='agent-test'); upd.add_argument('--reason',default=''); upd.add_argument('--ref'); upd.add_argument('--replay-receipt')
 rp=sub.add_parser('replay'); rp.add_argument('request_id'); rp.add_argument('--expected',choices=('supported','contradicted','insufficient_evidence')); rp.add_argument('--mode',choices=('original','current'),default='original')
 source=sub.add_parser('source'); ss=source.add_subparsers(dest='source_command'); sr=ss.add_parser('register'); sr.add_argument('path'); su=ss.add_parser('summarize'); su.add_argument('ref_id'); sf=ss.add_parser('fetch'); sf.add_argument('ref_id'); sf.add_argument('--lines'); sf.add_argument('--errors'); sf.add_argument('--pattern'); sf.add_argument('--context',type=int,default=2)
 regression=sub.add_parser('regression'); regression.add_argument('manifest'); regression.add_argument('--capture',action='store_true'); regression.add_argument('--endpoint'); regression.add_argument('--model'); regression.add_argument('--mode',choices=('json_schema','json_object','plain'))
 a=p.parse_args()
 try:
  if a.command=='source':
   if a.source_command=='register': _emit(evidence.register(a.path)); return
   if a.source_command=='summarize': _emit(evidence.summarize(a.ref_id)); return
   _emit(evidence.fetch(a.ref_id,a.lines,a.errors,a.pattern,a.context)); return
  if a.command=='doctor':
   missing=[x for x in ('BASE_URL','MODEL') if not _env(x)]
   if missing or not a.probe: _emit({'status':'unavailable' if missing else 'configured','missing':missing,'probed':False}); return
   import urllib.request, urllib.parse
   url=_env('BASE_URL'); u=urllib.parse.urlsplit(url)
   if u.scheme not in ('http','https') or not u.hostname or u.username or u.password: _emit({'status':'unavailable','missing':[],'probed':True,'error_code':'invalid_endpoint'}); return
   key=_env('API_KEY')
   key_file=_env('API_KEY_FILE')
   if not key and key_file:
    try: key=open(key_file).read().strip()
    except OSError: _emit({'status':'unavailable','missing':[],'probed':True,'error_code':'key_file_unavailable'}); return
   req=urllib.request.Request(url.rstrip('/')+'/models',headers={'Authorization':'Bearer '+key} if key else {})
   try:
    with urllib.request.urlopen(req,timeout=_timeout(_env('TIMEOUT','90'))) as response: data=json.loads(response.read(1000000))
    ok=response.status==200 and isinstance(data,dict) and isinstance(data.get('data'),list) and any(isinstance(m,dict) and m.get('id')==_env('MODEL') for m in data['data'])
    _emit({'status':'configured' if ok else 'unavailable','missing':[],'probed':True,'error_code':None if ok else 'invalid_models_response'})
   except Exception: _emit({'status':'unavailable','missing':[],'probed':True,'error_code':'probe_failed'})
   return
  if a.command=='judge-claims':
   raw=sys.stdin.buffer.read(100001)
   if len(raw)>100000: raise Rejected('packet_bytes_limit','serialized battery exceeds byte limit')
   packet=json.loads(raw); result=judge_claims(packet,capture=getattr(a,'capture',False)); _emit(result); return
  if a.command in ('judge',None):
   raw=sys.stdin.buffer.read(50001)
   if len(raw)>50000: raise Rejected('packet_bytes_limit','serialized packet exceeds byte limit')
   packet=json.loads(raw); result=judge(packet,capture=getattr(a,'capture',False)); _emit(result); return
  if a.command=='receipts':
   rows=_rows(_paths()[0])
   if a.receipts_command=='show':
    row=next((r for r in rows if r.get('request_id')==a.request_id),None)
    if row is None: raise Rejected('unknown_request_id','receipt not found')
    _emit(row); return
   if a.receipts_command=='export' and a.format=='jsonl': print('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)); return
   _emit(rows if a.receipts_command=='export' else {'rows':rows}); return
  if a.command=='replay': _emit(replay(a.request_id,a.expected,a.mode)); return
  if a.command=='feedback':
   rp_path,fp,_=_paths()
   if a.feedback_command in ('list','export'):
    rows=_rows(fp)
    if a.feedback_command=='export' and a.format=='jsonl': print('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows))
    else: _emit(rows if a.feedback_command=='export' else {'rows':rows})
    return
   receipts=_rows(rp_path); receipt=next((x for x in receipts if x.get('request_id')==a.request_id),None)
   if not receipt: raise Rejected('unknown_request_id','receipt not found')
   observed=receipt.get('verdict')
   if a.observed_verdict is not None and a.observed_verdict!=observed: raise Rejected('observed_verdict_mismatch','observed verdict differs from receipt')
   observed_status=receipt.get('status') or ('judged' if observed else None)
   if observed_status not in ('judged','invalid_model_output','unavailable'): raise Rejected('feedback_status_unsupported','receipt status cannot be tracked')
   issue_id=uuid.uuid4().hex; stamp=datetime.now(timezone.utc).isoformat()
   _append(fp,{'record_type':'issue','issue_id':issue_id,'request_id':a.request_id,'timestamp':stamp,'observed_verdict':observed,'observed_status':observed_status,'error_code':receipt.get('failure_code'),'expected':a.expected,'kind':a.kind,'reason':a.reason[:500]})
   _append(fp,{'record_type':'transition','issue_id':issue_id,'from':None,'to':'open','timestamp':stamp,'kind':a.kind,'reason':'feedback created'})
   _emit({'status':'recorded','issue_id':issue_id,'request_id':a.request_id,'kind':a.kind}); return
  if a.command=='issue':
   rp_path=_paths()[0]
   allissues=_issues(); events=_issue_events(); byid={x['issue_id']:x for x in allissues}
   if a.issue_command=='list': _emit([dict(x,status=next((e['to'] for e in reversed(events) if e['issue_id']==x['issue_id']),'open')) for x in allissues]); return
   if a.issue_command=='show':
    if a.issue_id not in byid: raise Rejected('unknown_issue_id','issue not found')
    _emit({'issue':byid[a.issue_id],'transitions':[e for e in events if e['issue_id']==a.issue_id]}); return
   if a.issue_id not in byid: raise Rejected('unknown_issue_id','issue not found')
   prior=[e for e in events if e['issue_id']==a.issue_id]; current=prior[-1]['to'] if prior else 'open'
   allowed={'open':('confirmed','fixed'),'confirmed':('fixed','open'),'fixed':('regression_tested','open'),'regression_tested':('open',)}
   if a.status not in allowed.get(current,()): raise Rejected('invalid_issue_transition','transition not allowed')
   if a.status=='fixed' and not a.ref: raise Rejected('fix_reference_required','fixed requires --ref')
   proof=None
   if a.status=='regression_tested':
    if not a.replay_receipt: raise Rejected('regression_proof_required','regression_tested requires --replay-receipt')
    proof=next((r for r in _rows(rp_path) if r.get('request_id')==a.replay_receipt and r.get('parent_request_id')==byid[a.issue_id]['request_id'] and r.get('status')=='judged' and r.get('verdict')==byid[a.issue_id]['expected']),None)
    if not proof: raise Rejected('invalid_regression_proof','receipt must be a successful matching replay of issue request')
   _append(_paths()[1],{'record_type':'transition','issue_id':a.issue_id,'from':current,'to':a.status,'timestamp':datetime.now(timezone.utc).isoformat(),'kind':a.kind,'reason':a.reason[:500],'reference':a.ref,'replay_receipt':proof.get('request_id') if proof else None})
   _emit({'status':'recorded','issue_id':a.issue_id,'from':current,'to':a.status}); return
  if a.command=='regression':
   from .core import validate
   try: raw=open(a.manifest,'rb').read(); manifest=json.loads(raw)
   except (OSError,ValueError): raise Rejected('invalid_manifest','manifest is unreadable or malformed')
   cases=manifest.get('cases') if isinstance(manifest,dict) else None
   if not isinstance(cases,list) or not cases: raise Rejected('invalid_manifest','manifest requires nonempty cases array')
   seen=set(); packets=[]
   try:
    for case in cases:
     if not isinstance(case,dict) or not isinstance(case.get('id'),str) or not case['id'] or case['id'] in seen or case.get('expected') not in ('supported','contradicted','insufficient_evidence') or not isinstance(case.get('evidence_ids'),list): raise ValueError()
     seen.add(case['id']); truth=case['evidence_ids']; offered={b['id'] for b in case['evidence']}
     if any(not isinstance(i,str) or i not in offered for i in truth): raise ValueError()
     packet={'claim':case['claim'],'evidence':case['evidence'],'flow':case.get('flow','direct'),'request_id':case['id']}; validate(packet); packets.append((case,packet))
   except Exception: raise Rejected('invalid_manifest','case schema, labels, ids, or packet is invalid')
   config={'url':a.endpoint,'model':a.model,'output_mode':a.mode} if any((a.endpoint,a.model,a.mode)) else None
   results=[]; fails=0
   for case,packet in packets:
    actual=judge(packet,config,capture=a.capture)
    failed=actual['status']=='unavailable'
    fails=fails+1 if failed else 0
    actual_ids=actual.get('evidence_ids',[]); expected_ids=case['evidence_ids']; evidence_match=(actual.get('status')=='judged' and (actual_ids==expected_ids if case.get('check_evidence_ids',False) else set(expected_ids).issubset(set(actual_ids))))
    results.append({'case_id':case['id'],'expected':case['expected'],'expected_evidence_ids':expected_ids,'status':actual['status'],'actual':actual.get('verdict'),'actual_evidence_ids':actual_ids,'label_match':actual.get('status')=='judged' and actual.get('verdict')==case['expected'],'evidence_match':evidence_match,'request_id':actual['request_id'],'error_code':actual.get('error_code')})
    if fails>=3: break
   complete=len(results)==len(cases)
   _emit({'status':'complete' if complete else 'incomplete','manifest_hash':__import__('hashlib').sha256(raw).hexdigest(),'planned':len(cases),'attempted':len(results),'remaining':len(cases)-len(results),'results':results}); return
  p.print_help()
 except Rejected as e: _emit({'status':'rejected','error_code':e.code,'error':str(e)})
 except evidence.EvidenceError as e: _emit({'status':'error','error_code':e.code,**e.details})
 except (json.JSONDecodeError,UnicodeDecodeError): _emit({'status':'rejected','error_code':'invalid_json'})
 except OSError: _emit({'status':'unavailable','error_code':'persistence_failed'})
if __name__=='__main__': main()
