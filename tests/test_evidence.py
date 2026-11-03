import json, os, pathlib, tempfile, unittest
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
if __name__=='__main__':unittest.main()
