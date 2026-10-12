# Retained Antenna headless regression harness, now targeting this candidate.
import sys
from pathlib import Path
HEADLESS=Path(__file__).resolve().parents[1]/'hermes/headless'
sys.path.insert(0,str(HEADLESS))
import asyncio,json,os,tempfile,unittest
from pathlib import Path
from bridge import Bridge,Refused
class Response:
 def __init__(self,value):self.value=value
 def raise_for_status(self):pass
 def json(self):return self.value
class HTTP:
 def __init__(self,rows,path):self.rows=rows;self.path=path
 async def get(self,url,**kwargs):
  if url.endswith('/latest-descendant'):return Response({'path':self.path,'session_id':self.path[-1]})
  return Response(self.rows[url.rsplit('/',1)[-1]])
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);os.chmod(self.root,0o700)
  self.token=self.root/'token';self.token.write_text('fixture');self.token.chmod(0o600)
  self.config=self.root/'config.json'
  self.c={'origin':'http://127.0.0.1:1234','token_file':str(self.token),'state_dir':str(self.root),'grants':{'peer':['agent:main:root']}}
  self.write()
 def tearDown(self):self.tmp.cleanup()
 def write(self):self.config.write_text(json.dumps(self.c));self.config.chmod(0o600)
 def rows(self):return {'root':{'id':'root','profile':'default','end_reason':'compression'},'tip':{'id':'tip','profile':'default','parent_session_id':'root','source':'tui'}}
 def lineage(self,rows=None,path=None):return asyncio.run(Bridge(self.config).lineage(HTTP(rows or self.rows(),path or ['root','tip']),'root'))
 def test_valid_compression_chain(self):self.assertEqual(self.lineage(),'tip')
 def test_branch_denied(self):
  r=self.rows();r['tip']['model_config']={'_branched_from':'root'}
  with self.assertRaises(Refused):self.lineage(r)
 def test_unrelated_parent_denied(self):
  r=self.rows();r['tip']['parent_session_id']='other'
  with self.assertRaises(Refused):self.lineage(r)
 def test_noncompression_parent_denied(self):
  r=self.rows();r['root']['end_reason']='closed'
  with self.assertRaises(Refused):self.lineage(r)
 def test_crossprofile_denied(self):
  r=self.rows();r['tip']['profile']='other'
  with self.assertRaises(Refused):self.lineage(r)
 def test_cycle_denied(self):
  with self.assertRaises(Refused):self.lineage(path=['root','tip','root'])
 def test_ungranted_target_denied(self):
  with self.assertRaises(Refused):Bridge(self.config).target('agent:main:other')
 def test_remote_endpoint_denied(self):
  self.c['origin']='http://192.0.2.1:1234';self.write()
  with self.assertRaises(Refused):Bridge(self.config)
 def test_loose_token_denied(self):
  self.token.chmod(0o644)
  with self.assertRaises(Refused):Bridge(self.config)
 def test_symlink_token_denied(self):
  alias=self.root/'alias';alias.symlink_to(self.token);self.c['token_file']=str(alias);self.write()
  with self.assertRaises(Refused):Bridge(self.config)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 raise SystemExit(0 if result.wasSuccessful() else 1)
