import json, os, pathlib, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
from jev.core import judge, strict_result, validate, Rejected

class Fake(BaseHTTPRequestHandler):
 mode='ok'; calls=0; last_body=None
 def do_GET(self):
  if self.path.endswith('/models'):
   data=json.dumps({'data':[{'id':'configured'}]}).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(data)
  else: self.send_error(404)
 def do_POST(self):
  type(self).calls+=1; body=json.loads(self.rfile.read(int(self.headers['Content-Length']))); type(self).last_body=body
  if self.path.endswith('/chat/completions'):
   if type(self).mode=='failure': self.send_error(503); return
   text=('{"verdict":"supported","evidence_ids":["e1"],"rationale":"The supplied fact matches."}' if type(self).mode=='ok' else '{"verdict":"supported","evidence_ids":["secret"],"rationale":"bad"}')
   payload={'model':'returned-model','choices':[{'finish_reason':'stop','message':{'content':text}}]}
   if type(self).mode=='large': payload['provider_metadata']='x'*70000
   data=json.dumps(payload).encode()
  else: self.send_error(404); return
  self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(data)
 def log_message(self,*a): return None

class Targeted(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=HTTPServer(('127.0.0.1',0),Fake); cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start(); cls.url=f'http://127.0.0.1:{cls.server.server_port}/v1'
 @classmethod
 def tearDownClass(cls): cls.server.shutdown(); cls.thread.join()
 def test_validation_and_locator_labels(self):
  for block in ({'id':'e'}, {'id':'e','text':''}, {'id':'e','text':'  '}):
   with self.assertRaises(Rejected): validate({'claim':'x','evidence':[block]})
  for src in ('repo:src/a.py','sheet:tab!A1','email:message-42','https://example.org/x'):
   validate({'claim':'x','evidence':[{'id':'e','text':'fact','source':src}]})
  for src in ('https://user:example-password@example.org/a','http://u@example.org','ftp://example.org/a'):
   with self.assertRaises(Rejected): validate({'claim':'x','evidence':[{'id':'e','text':'fact','source':src}]})
 def test_strict_result_preserves_valid_ids_on_abstention(self):
  x=strict_result('{"verdict":"insufficient_evidence","evidence_ids":["e1"],"rationale":"unclear"}',{'e1'},'stop'); self.assertEqual(x['evidence_ids'],['e1'])
 def test_empty_evidence_is_offline_but_receipted_and_timeout_bounds(self):
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d,'JEV_BASE_URL':self.url,'JEV_MODEL':'configured','JEV_TIMEOUT':'0'}):
   Fake.calls=0; r=judge({'claim':'x','evidence':[]}); self.assertEqual(r['error_code'],'invalid_timeout'); self.assertEqual(Fake.calls,0)
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d,'JEV_BASE_URL':self.url,'JEV_MODEL':'configured','JEV_API_KEY':'TOPSECRET'}):
   Fake.calls=0; r=judge({'claim':'x','evidence':[]}); self.assertEqual(r['verdict'],'insufficient_evidence'); self.assertEqual(Fake.calls,0); self.assertEqual(r['persistence'],'recorded')
   row=json.loads(pathlib.Path(d,'receipts.jsonl').read_text()); self.assertIn('timeout',row); self.assertNotIn('TOPSECRET',json.dumps(row))
 def test_fake_http_success_invalid_and_operational_failure(self):
  packet={'claim':'fact is true','evidence':[{'id':'e1','text':'fact is true'}]}
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d,'JEV_API_KEY':'DO_NOT_LEAK'}):
   for mode,want in [('ok','judged'),('invalid','invalid_model_output'),('failure','unavailable')]:
    Fake.mode=mode; r=judge(packet,{'url':self.url,'model':'configured','timeout':2}); self.assertEqual(r['status'],want)
    if mode=='ok': self.assertEqual(r['model'],'returned-model')
    self.assertNotIn('DO_NOT_LEAK',json.dumps(r))
   receipts=pathlib.Path(d,'receipts.jsonl').read_text(); self.assertNotIn('DO_NOT_LEAK',receipts)
 def test_observation_cap_and_short_rationale_are_sent_to_provider(self):
  packet={'claim':'fact is true','evidence':[{'id':'e1','text':'fact is true'}]}
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d,'JEV_MAX_OUTPUT_TOKENS':'2400'}):
   Fake.mode='ok'; Fake.calls=0
   result=judge(packet,{'url':self.url,'model':'configured','timeout':2})
   self.assertEqual(result['status'],'judged'); self.assertEqual(Fake.calls,1)
   self.assertEqual(Fake.last_body['max_tokens'],2400)
   prompt=Fake.last_body['messages'][0]['content']
   self.assertIn('preferably under 400 characters',prompt)
   self.assertIn('never over 1200 characters',prompt)
   row=json.loads(pathlib.Path(d,'receipts.jsonl').read_text())
   self.assertEqual(row['max_output_tokens'],2400); self.assertEqual(row['prompt_version'],'3')
 def test_rationale_boundary_and_truncated_json_remain_rejected(self):
  def body(n): return json.dumps({'verdict':'supported','evidence_ids':['e1'],'rationale':'x'*n})
  self.assertEqual(len(strict_result(body(1200),{'e1'},'stop')['rationale']),1200)
  with self.assertRaisesRegex(ValueError,'rationale_too_long'): strict_result(body(1201),{'e1'},'stop')
  with self.assertRaisesRegex(ValueError,'truncated_output'): strict_result(body(10),{'e1'},'length')
 def test_json_schema_mode_is_explicit_and_never_retried(self):
  packet={'claim':'fact is true','evidence':[{'id':'e1','text':'fact is true'}]}
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d}):
   Fake.mode='ok'; Fake.calls=0
   r=judge(packet,{'url':self.url,'model':'configured','timeout':2,'output_mode':'json_schema'})
   self.assertEqual(r['status'],'judged'); self.assertEqual(Fake.calls,1)
   fmt=Fake.last_body['response_format']; self.assertEqual(fmt['type'],'json_schema'); self.assertTrue(fmt['json_schema']['strict'])
 def test_mcp_sdk_subprocess_protocol_semantics_and_key_redaction(self):
  from mcp import ClientSession, StdioServerParameters
  from mcp.client.stdio import stdio_client
  import asyncio
  async def run():
   with tempfile.TemporaryDirectory() as d:
    env=dict(os.environ, PYTHONPATH='src',JEV_DATA_DIR=d,JEV_BASE_URL=self.url,JEV_MODEL='configured',JEV_API_KEY='NEVER_LEAK')
    params=StdioServerParameters(command=sys.executable,args=['-m','jev.mcp_server'],env=env)
    async with stdio_client(params) as (read,write):
     async with ClientSession(read,write) as session:
      await session.initialize()
      packet={'claim':'fact true','evidence':[{'id':'e1','text':'fact true'}]}
      for mode,status in [('ok','judged'),('invalid','invalid_model_output'),('failure','unavailable')]:
       Fake.mode=mode; r=await session.call_tool('jev_check_claim',packet); payload=json.loads(r.content[0].text); self.assertEqual(payload['status'],status)
       if mode=='ok': self.assertEqual(payload['verdict'],'supported')
       if mode!='ok': self.assertIn(payload['error_code'],('invalid_citations','provider_http_503'))
      empty=await session.call_tool('jev_check_claim',{'claim':'x','evidence':[]}); self.assertEqual(json.loads(empty.content[0].text)['verdict'],'insufficient_evidence')
    stored=''.join(p.read_text() for p in pathlib.Path(d).glob('**/*') if p.is_file())
    self.assertNotIn('NEVER_LEAK',stored)
  asyncio.run(run())
 def test_cli_stdin_matches_mcp_semantic_without_network(self):
  packet={'claim':'x','evidence':[]}
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d,'JEV_BASE_URL':self.url,'JEV_MODEL':'configured'}):
   cli=subprocess.run([sys.executable,'-m','jev.cli','judge'],input=json.dumps(packet),text=True,capture_output=True,env=dict(os.environ,PYTHONPATH='src'),check=True)
   cli_result=json.loads(cli.stdout)
   self.assertEqual(cli_result['verdict'],'insufficient_evidence'); self.assertEqual(cli.stderr,'')
   import asyncio
   from mcp import ClientSession, StdioServerParameters
   from mcp.client.stdio import stdio_client
   async def call():
    params=StdioServerParameters(command=sys.executable,args=['-m','jev.mcp_server'],env=dict(os.environ,PYTHONPATH='src'))
    async with stdio_client(params) as (rd,wr):
     async with ClientSession(rd,wr) as session:
      await session.initialize(); response=await session.call_tool('jev_check_claim',packet); return json.loads(response.content[0].text)
   mcp_result=asyncio.run(call())
   self.assertEqual((cli_result['status'],cli_result['verdict'],cli_result['evidence_ids']),(mcp_result['status'],mcp_result['verdict'],mcp_result['evidence_ids']))
 def test_client_label_param_and_env_fallback_on_receipt(self):
  from mcp import ClientSession, StdioServerParameters
  from mcp.client.stdio import stdio_client
  import asyncio
  async def run():
   with tempfile.TemporaryDirectory() as d:
    env=dict(os.environ, PYTHONPATH='src',JEV_DATA_DIR=d,JEV_BASE_URL=self.url,JEV_MODEL='configured',JEV_CLIENT_NAME='alma')
    params=StdioServerParameters(command=sys.executable,args=['-m','jev.mcp_server'],env=env)
    async with stdio_client(params) as (read,write):
     async with ClientSession(read,write) as session:
      await session.initialize()
      Fake.mode='ok'
      payload=json.loads((await session.call_tool('jev_check_claim',{'claim':'fact true','evidence':[{'id':'e1','text':'fact true'}],'client':'dsh'})).content[0].text)
      self.assertEqual(payload['status'],'judged')
      rows=[json.loads(x) for x in pathlib.Path(d,'receipts.jsonl').read_text().splitlines() if x]
      self.assertEqual(rows[-1]['client'],'dsh')
      payload=json.loads((await session.call_tool('jev_check_claim',{'claim':'fact true','evidence':[{'id':'e1','text':'fact true'}]})).content[0].text)
      rows=[json.loads(x) for x in pathlib.Path(d,'receipts.jsonl').read_text().splitlines() if x]
      self.assertEqual(rows[-1]['client'],'alma')
      bad=json.loads((await session.call_tool('jev_check_claim',{'claim':'x','evidence':[],'client':'has space'})).content[0].text)
      self.assertEqual((bad['status'],bad['error_code']),('rejected','invalid_client'))
  asyncio.run(run())
 def test_mcp_caller_request_id_persisted_to_receipt(self):
  from mcp import ClientSession, StdioServerParameters
  from mcp.client.stdio import stdio_client
  import asyncio
  async def run():
   with tempfile.TemporaryDirectory() as d:
    env=dict(os.environ, PYTHONPATH='src',JEV_DATA_DIR=d,JEV_BASE_URL=self.url,JEV_MODEL='configured')
    params=StdioServerParameters(command=sys.executable,args=['-m','jev.mcp_server'],env=env)
    async with stdio_client(params) as (read,write):
     async with ClientSession(read,write) as session:
      await session.initialize()
      Fake.mode='ok'
      payload=json.loads((await session.call_tool('jev_check_claim',{'claim':'fact true','evidence':[{'id':'e1','text':'fact true'}],'caller_request_id':'alma://thread/mw1g49a4abo51ms19c'})).content[0].text)
      self.assertEqual(payload['status'],'judged')
      rows=[json.loads(x) for x in pathlib.Path(d,'receipts.jsonl').read_text().splitlines() if x]
      self.assertEqual(rows[-1]['caller_request_id'],'alma://thread/mw1g49a4abo51ms19c')
      none=json.loads((await session.call_tool('jev_check_claim',{'claim':'fact true','evidence':[{'id':'e1','text':'fact true'}]})).content[0].text)
      self.assertEqual(none['status'],'judged')
      rows=[json.loads(x) for x in pathlib.Path(d,'receipts.jsonl').read_text().splitlines() if x]
      self.assertIsNone(rows[-1]['caller_request_id'])
  asyncio.run(run())
 def test_feedback_uses_receipt_and_rejects_false_observation(self):
  with tempfile.TemporaryDirectory() as d:
   env=dict(os.environ,PYTHONPATH='src',JEV_DATA_DIR=d)
   pathlib.Path(d).mkdir(parents=True,exist_ok=True)
   pathlib.Path(d,'receipts.jsonl').write_text(json.dumps({'request_id':'r1','verdict':'supported'})+'\n')
   bad=subprocess.run([sys.executable,'-m','jev.cli','feedback','add','r1','contradicted','--observed-verdict','contradicted'],text=True,capture_output=True,env=env,check=True)
   self.assertEqual(json.loads(bad.stdout)['error_code'],'observed_verdict_mismatch')
   good=subprocess.run([sys.executable,'-m','jev.cli','feedback','add','r1','contradicted'],text=True,capture_output=True,env=env,check=True)
   self.assertEqual(json.loads(good.stdout)['status'],'recorded')
   rows=[json.loads(x) for x in pathlib.Path(d,'feedback.jsonl').read_text().splitlines()]; row=rows[0]; self.assertEqual(row['observed_verdict'],'supported'); self.assertEqual(row['kind'],'agent-test'); self.assertTrue(row['timestamp']); self.assertEqual(rows[1]['to'],'open')
 def test_receipt_list_show_and_export_commands(self):
  with tempfile.TemporaryDirectory() as d:
   env=dict(os.environ,PYTHONPATH='src',JEV_DATA_DIR=d)
   row={'request_id':'r1','status':'judged','verdict':'supported'}
   pathlib.Path(d,'receipts.jsonl').write_text(json.dumps(row)+'\n')
   listed=json.loads(subprocess.run([sys.executable,'-m','jev.cli','receipts','list'],text=True,capture_output=True,env=env,check=True).stdout)
   shown=json.loads(subprocess.run([sys.executable,'-m','jev.cli','receipts','show','r1'],text=True,capture_output=True,env=env,check=True).stdout)
   exported=json.loads(subprocess.run([sys.executable,'-m','jev.cli','receipts','export'],text=True,capture_output=True,env=env,check=True).stdout)
   self.assertEqual(listed['rows'],[row]); self.assertEqual(shown,row); self.assertEqual(exported,[row])
 def test_cli_capture_current_replay_links_original(self):
  with tempfile.TemporaryDirectory() as d:
   Fake.mode='ok'
   env=dict(os.environ,PYTHONPATH='src',JEV_DATA_DIR=d,JEV_BASE_URL=self.url,JEV_MODEL='configured',JEV_CAPTURE='1')
   packet={'claim':'fact true','evidence':[{'id':'e1','text':'fact true'}]}
   first=subprocess.run([sys.executable,'-m','jev.cli','judge'],input=json.dumps(packet),text=True,capture_output=True,env=env,check=True)
   original=json.loads(first.stdout)
   replayed=subprocess.run([sys.executable,'-m','jev.cli','replay',original['request_id'],'--expected','supported','--mode','current'],text=True,capture_output=True,env=env,check=True)
   result=json.loads(replayed.stdout); self.assertEqual(result['status'],'judged'); self.assertTrue(result['match']); self.assertEqual(result['parent_request_id'],original['request_id'])
   rows=[json.loads(x) for x in pathlib.Path(d,'receipts.jsonl').read_text().splitlines()]; self.assertEqual(rows[-1]['parent_request_id'],rows[0]['request_id'])
 def test_issue_transitions_require_linked_replay_proof(self):
  with tempfile.TemporaryDirectory() as d:
   Fake.mode='ok'
   env=dict(os.environ,PYTHONPATH='src',JEV_DATA_DIR=d,JEV_BASE_URL=self.url,JEV_MODEL='configured',JEV_CAPTURE='1')
   packet={'claim':'fact true','evidence':[{'id':'e1','text':'fact true'}]}
   first=json.loads(subprocess.run([sys.executable,'-m','jev.cli','judge'],input=json.dumps(packet),text=True,capture_output=True,env=env,check=True).stdout)
   issue=json.loads(subprocess.run([sys.executable,'-m','jev.cli','feedback','add',first['request_id'],'supported'],text=True,capture_output=True,env=env,check=True).stdout)['issue_id']
   def update(status,*args): return json.loads(subprocess.run([sys.executable,'-m','jev.cli','issue','update',issue,status,*args],text=True,capture_output=True,env=env,check=True).stdout)
   self.assertEqual(update('fixed')['error_code'],'fix_reference_required')
   self.assertEqual(update('confirmed')['status'],'recorded')
   self.assertEqual(update('fixed','--ref','commit:abc')['status'],'recorded')
   self.assertEqual(update('regression_tested')['error_code'],'regression_proof_required')
   replayed=json.loads(subprocess.run([sys.executable,'-m','jev.cli','replay',first['request_id'],'--expected','supported','--mode','current'],text=True,capture_output=True,env=env,check=True).stdout)
   self.assertEqual(update('regression_tested','--replay-receipt',replayed['request_id'])['status'],'recorded')
 def test_feedback_tracks_failed_receipts_and_requires_matching_observation(self):
  with tempfile.TemporaryDirectory() as d:
   env=dict(os.environ,PYTHONPATH='src',JEV_DATA_DIR=d); pathlib.Path(d,'receipts.jsonl').write_text(json.dumps({'request_id':'bad','status':'invalid_model_output','failure_code':'invalid_citations'})+chr(10))
   result=json.loads(subprocess.run([sys.executable,'-m','jev.cli','feedback','add','bad','supported'],text=True,capture_output=True,env=env,check=True).stdout)
   issue=json.loads(subprocess.run([sys.executable,'-m','jev.cli','issue','show',result['issue_id']],text=True,capture_output=True,env=env,check=True).stdout)['issue']
   self.assertIsNone(issue['observed_verdict']); self.assertEqual(issue['observed_status'],'invalid_model_output'); self.assertEqual(issue['error_code'],'invalid_citations')
   subprocess.run([sys.executable,'-m','jev.cli','issue','update',result['issue_id'],'confirmed'],text=True,capture_output=True,env=env,check=True)
   subprocess.run([sys.executable,'-m','jev.cli','issue','update',result['issue_id'],'fixed','--ref','test:fix'],text=True,capture_output=True,env=env,check=True)
   blocked=subprocess.run([sys.executable,'-m','jev.cli','issue','update',result['issue_id'],'regression_tested','--replay-receipt','fake'],text=True,capture_output=True,env=env,check=True)
   self.assertEqual(json.loads(blocked.stdout)['error_code'],'invalid_regression_proof')
 def test_capture_response_only_and_storage_failure(self):
  packet={'claim':'fact true','evidence':[{'id':'e1','text':'fact true'}]}
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d}):
   Fake.mode='ok'; r=judge(packet,{'url':self.url,'model':'configured'},capture_response=True); row=json.loads(pathlib.Path(d,'receipts.jsonl').read_text())
   self.assertTrue(pathlib.Path(row['capture_path']).exists()); self.assertIsNone(json.loads(pathlib.Path(row['capture_path']).read_text())['packet'])
   from jev.core import replay
   with self.assertRaises(Rejected) as ctx: replay(r['request_id'],'supported','current')
   self.assertEqual(ctx.exception.code,'non_replayable')
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d,'JEV_CAPTURE':'1','JEV_CAPTURE_DIR':str(pathlib.Path(d,'not-a-directory'))}):
   pathlib.Path(d,'not-a-directory').write_text('block')
   r=judge({'claim':'x','evidence':[]}); self.assertEqual(r['status'],'judged'); self.assertEqual(r['capture_persistence'],'failed'); self.assertEqual(r['capture_error'],'capture_storage_failed')
   receipt=json.loads(pathlib.Path(d,'receipts.jsonl').read_text()); self.assertEqual(receipt['capture_error'],'capture_storage_failed')
 def test_truncated_raw_response_allows_current_but_not_original_replay(self):
  from jev.core import replay
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d,'JEV_CAPTURE':'1','JEV_CAPTURE_RESPONSE':'1','JEV_BASE_URL':self.url,'JEV_MODEL':'configured'}):
   Fake.mode='large'; packet={'claim':'fact','evidence':[{'id':'e1','text':'fact'}]}; first=judge(packet,capture=True,capture_response=True); receipt=json.loads(pathlib.Path(d,'receipts.jsonl').read_text()); cap=json.loads(pathlib.Path(receipt['capture_path']).read_text())
   self.assertTrue(cap['captured_response']['truncated']); Fake.mode='ok'
   current=replay(first['request_id'],'supported','current'); self.assertEqual(current['status'],'judged')
   with self.assertRaises(Rejected) as ctx: replay(first['request_id'],mode='original')
   self.assertEqual(ctx.exception.code,'capture_truncated')
 def test_schema_and_source_fingerprints_and_failed_replay_guard(self):
  from jev.core import _schema_hash,_json_hash,OUTPUT_SCHEMA,_wire_schema
  packet={'claim':'x','evidence':[{'id':'z','text':'y'}]}; wire=_wire_schema(packet)
  self.assertNotEqual(_schema_hash(),_json_hash(wire)); self.assertNotIn('uniqueItems',wire['properties']['evidence_ids']); self.assertEqual(wire['properties']['evidence_ids']['items']['enum'],['z'])
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d,'JEV_CAPTURE':'1'}):
   Fake.mode='invalid'; r=judge(packet,{'url':self.url,'model':'configured'}); receipt=json.loads(pathlib.Path(d,'receipts.jsonl').read_text())
   self.assertEqual(receipt['source_fingerprint']['hash'],_json_hash(receipt['source_fingerprint']['files'])); self.assertIn('files',receipt['source_fingerprint'])
   cap=json.loads(pathlib.Path(receipt['capture_path']).read_text()); self.assertEqual(_json_hash(cap['output_schema']),receipt['output_schema_hash']); self.assertEqual(_json_hash(cap['wire_schema']),receipt['wire_schema_hash'])
   from jev.core import replay
   with self.assertRaises(Rejected): replay(r['request_id'],mode='original')
 def test_doctor_probe_and_jsonl_export(self):
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'JEV_DATA_DIR':d,'JEV_BASE_URL':self.url,'JEV_MODEL':'configured','PYTHONPATH':'src'}):
   r=subprocess.run([sys.executable,'-m','jev.cli','doctor','--probe'],text=True,capture_output=True,env=os.environ.copy(),check=True)
   self.assertEqual(json.loads(r.stdout)['status'],'configured'); self.assertTrue(json.loads(r.stdout)['probed'])
   pathlib.Path(d,'feedback.jsonl').write_text('{"record_type":"issue"}'+chr(10)+'{"record_type":"transition"}'+chr(10))
   out=subprocess.run([sys.executable,'-m','jev.cli','feedback','export','--format','jsonl'],text=True,capture_output=True,env=os.environ.copy(),check=True)
   self.assertEqual(len(out.stdout.splitlines()),2); [json.loads(line) for line in out.stdout.splitlines()]
 def test_invalid_regression_manifest_does_not_call_provider(self):
  with tempfile.TemporaryDirectory() as d:
   manifest=pathlib.Path(d,'bad.json'); manifest.write_text('{"cases":[{"id":"x","claim":"x","evidence":[],"expected":"wrong","evidence_ids":[]}]}')
   env=dict(os.environ,PYTHONPATH='src',JEV_BASE_URL=self.url,JEV_MODEL='configured',JEV_DATA_DIR=str(pathlib.Path(d,'data'))); Fake.calls=0
   r=subprocess.run([sys.executable,'-m','jev.cli','regression',str(manifest)],text=True,capture_output=True,env=env,check=True)
   self.assertEqual(json.loads(r.stdout)['error_code'],'invalid_manifest'); self.assertEqual(Fake.calls,0)
 def test_mcp_evidence_tools_and_stale_source(self):
  from mcp import ClientSession, StdioServerParameters
  from mcp.client.stdio import stdio_client
  import asyncio
  async def run():
   with tempfile.TemporaryDirectory() as d:
    output=pathlib.Path(d,'output.txt'); output.write_text('Tests run: 2, Failures: 0, Errors: 0, Skipped: 0\n')
    env=dict(os.environ,PYTHONPATH='src',JEV_DATA_DIR=str(pathlib.Path(d,'data')))
    async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','jev.mcp_server'],env=env)) as (rd,wr):
     async with ClientSession(rd,wr) as session:
      await session.initialize(); tools=await session.list_tools(); self.assertEqual(len(tools.tools),3)
      cli=subprocess.run([sys.executable,'-m','jev.cli','source','register',str(output)],capture_output=True,text=True,env=env,check=True); ref=json.loads(cli.stdout)['ref_id']
      sm=await session.call_tool('jev_summarize_output',{'source_ref':ref}); self.assertEqual(json.loads(sm.content[0].text)['status'],'pass')
      got=await session.call_tool('jev_fetch_evidence',{'source_ref':ref,'lines':'1:1'}); self.assertEqual(json.loads(got.content[0].text)['lines'][0]['line'],1)
      output.write_text('changed\n'); stale=await session.call_tool('jev_summarize_output',{'source_ref':ref}); self.assertEqual(json.loads(stale.content[0].text)['error_code'],'stale_source')
  asyncio.run(run())

if __name__=='__main__': unittest.main()
