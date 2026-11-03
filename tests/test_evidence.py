import json, os, pathlib, subprocess, sys, tempfile, unittest
from unittest.mock import patch
from jev import evidence

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.env=patch.dict(os.environ,{'JEV_DATA_DIR':self.tmp.name}); self.env.start(); self.addCleanup(self.env.stop)
 def source(self,text):
  p=pathlib.Path(self.tmp.name)/'input.txt'; p.write_text(text); return evidence.register(str(p))
 def test_maven_and_fetch(self):
  r=self.source('Tests run: 4, Failures: 1, Errors: 0, Skipped: 1\n09:03:02 [main] ERROR app - bad\n')
  s=evidence.summarize(r['ref_id']); self.assertEqual(s['counts']['tests_total'],4); self.assertEqual(s['first_failure']['line'],2)
  self.assertEqual(evidence.fetch(r['ref_id'],lines='2:2')['lines'][0]['line'],2)
 def test_stale_and_missing(self):
  r=self.source('1 passed\n'); pathlib.Path(r['path']).write_text('2 passed\n')
  with self.assertRaises(evidence.EvidenceError) as e:evidence.summarize(r['ref_id'])
  self.assertEqual(e.exception.code,'stale_source')
  pathlib.Path(r['path']).unlink()
  with self.assertRaises(evidence.EvidenceError) as e:evidence.fetch(r['ref_id'],lines='1:1')
  self.assertEqual(e.exception.code,'source_unavailable')
 def test_summary_preview_and_modes(self):
  r=self.source('preview 0 errors\n'+''.join(f'ERROR failure {i}\n' for i in range(15)))
  s=evidence.summarize(r['ref_id']); self.assertEqual(s['display']['total_event_count'],15); self.assertEqual(s['display']['shown_event_count'],10); self.assertFalse(s['display']['complete'])
 def test_generic_and_limit(self):
  r=self.source('3 passed, 1 failed, 2 skipped\n')
  self.assertEqual(evidence.summarize(r['ref_id'])['status'],'fail')
  with self.assertRaises(evidence.EvidenceError): evidence.fetch(r['ref_id'],lines='1:201')
 def test_permissions(self):
  r=self.source('ok'); self.assertEqual(os.stat(pathlib.Path(self.tmp.name)/'sources.jsonl').st_mode & 0o777,0o600)
  self.assertEqual(os.stat(self.tmp.name).st_mode & 0o777,0o700)
 def test_error_header_overrides_generic_passed(self):
  r=self.source('3 passed\n[ERROR] build broke\n')
  self.assertEqual(evidence.summarize(r['ref_id'])['status'],'fail')
 def test_error_header_overrides_zero_totals(self):
  r=self.source('Tests run: 3, Failures: 0, Errors: 0, Skipped: 0\nERROR build broke\n')
  self.assertEqual(evidence.summarize(r['ref_id'])['status'],'fail')
 def test_no_patterns_is_unknown_with_null_totals(self):
  r=self.source('output was inconclusive\n')
  result=evidence.summarize(r['ref_id'])
  self.assertEqual(result['status'],'unknown')
  self.assertTrue(all(result['counts'][k] is None for k in ('tests_total','passed','failed','errors','skipped')))
  self.assertIn('detection_scope',result); self.assertIn('detection_notes',result)
 def test_last_maven_total_wins_with_multidigit_values(self):
  r=self.source('Tests run: 123, Failures: 4, Errors: 2, Skipped: 10\nTests run: 234, Failures: 12, Errors: 3, Skipped: 20\n')
  counts=evidence.summarize(r['ref_id'])['counts']
  self.assertEqual((counts['tests_total'],counts['failed'],counts['errors'],counts['skipped'],counts['passed']),(234,12,3,20,199))
 def test_fetch_truncation_and_totals(self):
  r=self.source('before\n'+''.join(f'ERROR problem {i}\n' for i in range(5))+'after\n')
  empty=evidence.fetch(r['ref_id'],lines='1:1')
  self.assertEqual(empty['lines'][0]['line'],1)
  errors=evidence.fetch(r['ref_id'],errors='2',context=0)
  self.assertTrue(errors['truncated']['lines']); self.assertEqual(errors['total_errors_in_source'],5)
  pats=evidence.fetch(r['ref_id'],pattern='ERROR',context=0)
  self.assertEqual(pats['total_matches_in_source'],5); self.assertFalse(pats['truncated']['lines'])
 def test_lines_clamped_at_eof_marks_truncated(self):
  r=self.source('only line\n')
  result=evidence.fetch(r['ref_id'],lines='1:3')
  self.assertTrue(result['truncated']['lines'])
 def test_pattern_with_context(self):
  r=self.source('first\nneedle\nlast\n')
  result=evidence.fetch(r['ref_id'],pattern='needle',context=1)
  self.assertEqual([x['line'] for x in result['lines']],[1,2,3])
  self.assertEqual(result['total_matches_in_source'],1)
 def test_cli_registers_stdin_source_end_to_end(self):
  env=dict(os.environ,PYTHONPATH='src',JEV_DATA_DIR=self.tmp.name)
  registered=subprocess.run([sys.executable,'-m','jev.cli','source','register','-'],input='Tests run: 2, Failures: 0, Errors: 0, Skipped: 0\n',text=True,capture_output=True,env=env,check=True)
  row=json.loads(registered.stdout)
  self.assertEqual(evidence.summarize(row['ref_id'])['status'],'pass')
  self.assertEqual(pathlib.Path(row['path']).read_text(),'Tests run: 2, Failures: 0, Errors: 0, Skipped: 0\n')
 def test_zero_returned_errors_still_reports_total(self):
  r=self.source('before\nERROR a\nERROR b\n')
  result=evidence.fetch(r['ref_id'],errors='0',context=0)
  self.assertEqual(result['lines'],[])
  self.assertTrue(result['truncated']['lines'])
  self.assertEqual(result['total_errors_in_source'],2)
if __name__=='__main__':unittest.main()
