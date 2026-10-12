import os,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'hermes/headless'))
from managed import child_environment

class ChildEnvironment(unittest.TestCase):
    def test_yolo_parent_does_not_change_child_launch_authority(self):
        for value in (None,'1','true','yes','0','false',''):
            parent=dict(os.environ,PROVIDER_API_KEY='fixture-only',HERMES_PROFILE='other',HERMES_INTERACTIVE='1',HERMES_SESSION_KEY='parent',HERMES_SINGLE_QUERY_SESSION='1',HERMES_ACP_AUTO_APPROVE='1')
            if value is not None:parent['HERMES_YOLO_MODE']=value
            else:parent.pop('HERMES_YOLO_MODE',None)
            env=child_environment(parent,{'home':'/selected/home'},'private-token','private-password')
            self.assertEqual(env['HERMES_YOLO_MODE'],'0');self.assertEqual(env['HERMES_HOME'],'/selected/home')
            self.assertEqual(env['PROVIDER_API_KEY'],'fixture-only')
            for key in ('HERMES_PROFILE','HERMES_INTERACTIVE','HERMES_SESSION_KEY','HERMES_SINGLE_QUERY_SESSION','HERMES_ACP_AUTO_APPROVE'):self.assertNotIn(key,env)
            self.assertEqual(parent.get('HERMES_YOLO_MODE'),value)
            # The actual spawned process receives the sanitized environment.
            p=subprocess.run([sys.executable,'-c','import os;assert os.environ["HERMES_YOLO_MODE"]=="0"'],env=env,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)

if __name__=='__main__':unittest.main()
