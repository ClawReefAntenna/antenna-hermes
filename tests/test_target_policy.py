import asyncio,importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'hermes/headless'
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('target_bridge',ROOT/'bridge.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TargetCheck(unittest.TestCase):
 def test_normal_saved_variants(self):
  for v in (None,{}, {'yolo_mode':False},'{"yolo_mode":false}'):
   with self.subTest(value=v):m.require_normal_target({'model_config':v})
 def test_yolo_refused(self):
  for v in ({'yolo_mode':True},'{"yolo_mode":true}'):
   with self.assertRaises(m.TargetPolicyRefused) as error:m.require_normal_target({'model_config':v})
   self.assertEqual(error.exception.reason,'headless_yolo_target')
 def test_unknown_saved_policy_refused(self):
  for v in ({},{'model_config':[]},{'model_config':'invalid'},{'model_config':{'yolo_mode':'false'}}):
   with self.subTest(value=v),self.assertRaises(m.TargetPolicyRefused):m.require_normal_target(v)
 def test_resumed_yolo_refused(self):
  with self.assertRaises(m.TargetPolicyRefused):m.require_normal_resume({'info':{'yolo':True}})
 def test_resumed_normal_allowed(self):m.require_normal_resume({'info':{'yolo':False}})
 def test_unknown_resumed_state_refused(self):
  for v in ({},{'info':{}},{'info':{'yolo':'false'}}):
   with self.subTest(value=v),self.assertRaises(m.TargetPolicyRefused):m.require_normal_resume(v)
 def test_check_resolved_target_not_historical_ancestor(self):
  class Response:
   def raise_for_status(self):pass
   def json(self):return {'path':['root','tip'],'session_id':'tip'}
  class HTTP:
   async def get(self,*a):return Response()
  for tip_yolo in (False,True):
   rows={'root':{'id':'root','end_reason':'compression','model_config':{'yolo_mode':True}},'tip':{'id':'tip','parent_session_id':'root','source':'desktop','model_config':{'yolo_mode':tip_yolo}}}
   b=object.__new__(m.Bridge)
   async def detail(http,key):return rows[key]
   b.detail=detail
   if tip_yolo:
    with self.assertRaises(m.TargetPolicyRefused):asyncio.run(b.lineage(HTTP(),'root'))
   else:self.assertEqual(asyncio.run(b.lineage(HTTP(),'root')),'tip')
if __name__=='__main__':unittest.main()
