import json, os, subprocess, sys, tempfile, unittest
from unittest.mock import patch
from jev.core import validate, Rejected, strict_result, judge

class CoreTests(unittest.TestCase):
 def test_strict_results(self):
  for result in [dict(verdict='supported',evidence_ids=[],rationale='yes'),dict(verdict='contradicted',evidence_ids=['e1'],rationale=' '),dict(verdict='supported',evidence_ids=['bad'],rationale='yes')]:
   with self.assertRaises(ValueError): strict_result(json.dumps(result),{'e1'},'stop')
  good=dict(verdict='insufficient_evidence',evidence_ids=[],rationale='unknown')
  self.assertEqual(strict_result(json.dumps(good),set(),'stop')['verdict'],'insufficient_evidence')
  for finish in ('length','content_filter','tool_calls',None):
   with self.assertRaises(ValueError): strict_result('{}',set(),finish)
 def test_validation_bounds_and_ids(self):
  with self.assertRaises(Rejected): validate({'claim':'x','evidence':[{'id':'a','text':'x'},{'id':'a','text':'x'}]})
  for rid in (2,[], ' '):
   with self.assertRaises(Rejected): validate({'claim':'x','evidence':[],'request_id':rid})
  with self.assertRaises(Rejected): validate({'claim':'x','evidence':[{'id':'x','text':'','scope':'s'*1001}]})
  with self.assertRaises(Rejected): validate({'claim':'x','evidence':[{'id':'x','text':'ok','source':'javascript:alert(1)'}]})
 def test_no_config_receipt_and_feedback_join(self):
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d},clear=True):
   r=judge({'claim':'A','evidence':[],'request_id':'caller'})
   self.assertEqual(r['status'],'judged'); self.assertEqual(r['verdict'],'insufficient_evidence'); self.assertEqual(r['caller_request_id'],'caller')
   rows=[json.loads(x) for x in open(os.path.join(d,'receipts.jsonl'))]; self.assertEqual(rows[0]['request_id'],r['request_id']); self.assertNotIn('rationale',rows[0]); self.assertNotIn('evidence',rows[0])
   env=dict(os.environ); env['JEV_DATA_DIR']=d; env['PYTHONPATH']='src'
   good=subprocess.run([sys.executable,'-m','jev.cli','feedback','add',r['request_id'],'supported'],env=env,input='',text=True,capture_output=True)
   self.assertEqual(json.loads(good.stdout)['kind'],'agent-test')
   self.assertNotIn('SECRET',open(os.path.join(d,'feedback.jsonl')).read())
   bad=subprocess.run([sys.executable,'-m','jev.cli','feedback','add','missing','supported'],env=env,text=True,capture_output=True)
   self.assertEqual(json.loads(bad.stdout)['error_code'],'unknown_request_id')
 def test_cli_help_and_json(self):
  for args in (['--help'],['judge','--help']):
   r=subprocess.run([sys.executable,'-m','jev.cli',*args],text=True,capture_output=True); self.assertEqual(r.returncode,0)
  with tempfile.TemporaryDirectory() as d:
   env=dict(os.environ); env['JEV_DATA_DIR']=d; env['PYTHONPATH']='src'
   r=subprocess.run([sys.executable,'-m','jev.cli'],input='{}',text=True,capture_output=True,env=env)
   self.assertEqual(json.loads(r.stdout)['status'],'rejected'); self.assertEqual(r.stderr,'')
 def test_capture_permissions_digest_and_replay_modes(self):
  from jev.core import load_capture, replay
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d},clear=True):
   packet={'claim':'A','evidence':[{'id':'x','text':'fact','scope':'s','source':'repo:a'}]}
   plain=judge(packet); row=json.loads(open(os.path.join(d,'receipts.jsonl')).readline())
   self.assertNotIn('capture_path',row); self.assertNotIn('claim',row); self.assertNotIn('evidence',row)
   captured=judge(packet,capture=True); receipt=[json.loads(x) for x in open(os.path.join(d,'receipts.jsonl'))][-1]
   cap_path=receipt['capture_path']; self.assertEqual(os.stat(cap_path).st_mode & 0o777,0o600)
   self.assertEqual(load_capture(receipt)['packet_hash'],receipt['input_hash'])
   with open(cap_path) as f: cap=json.load(f)
   cap['packet']['claim']='tampered'
   with open(cap_path,'w') as f: json.dump(cap,f)
   with self.assertRaises(Rejected): load_capture(receipt)
   with self.assertRaises(Rejected) as ctx: replay(plain['request_id'])
   self.assertEqual(ctx.exception.code,'non_replayable')
 def test_strict_schema_contract_and_stable_identity(self):
  from jev.core import OUTPUT_SCHEMA,_schema_hash,_json_hash
  self.assertFalse(OUTPUT_SCHEMA['additionalProperties'])
  self.assertEqual(_schema_hash(),_json_hash(OUTPUT_SCHEMA))
  self.assertEqual(strict_result('{"verdict":"insufficient_evidence","evidence_ids":[],"rationale":"unknown"}',set(),'stop')['verdict'],'insufficient_evidence')
  with self.assertRaises(ValueError): strict_result('{"verdict":"supported","evidence_ids":[],"rationale":"x"}',set(),'stop')
if __name__=='__main__': unittest.main()
