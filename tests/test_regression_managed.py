"""Production headless refusal and unchanged live-session service; no gate mocks."""
import asyncio,json,os,socket,subprocess,sys,tempfile,time,unittest,urllib.request
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'hermes/headless'))
import bridge
import hermes
from availability import REASON

class Managed(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='ant-stop-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.home=self.root/'home';self.home.mkdir(mode=0o700)
        self.cfg=self.home/'config.yaml';self.cfg.write_text('yolo_mode: true\napprovals: {mode: off}\n')
        (self.home/'.env').write_text('HERMES_YOLO_MODE=1\n')
        (self.home/'state.db').write_bytes(b'untouched session history fixture')
        self.before={p.name:p.read_bytes() for p in self.home.iterdir()}
        self.marker=self.root/'executed'
        self.launcher=self.root/'hermes'
        self.launcher.write_text('#!/bin/sh\ntouch '+str(self.marker)+'\n');self.launcher.chmod(0o700)
        self.settings=dict(enabled=True,python=sys.executable,hermes=str(self.launcher),home=str(self.home),port=19387,grants={'peer':['agent:main:saved']})
    def unchanged(self):
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.before,{p.name:p.read_bytes() for p in self.home.iterdir()})
        self.assertFalse((self.root/'headless-active.json').exists())
        self.assertFalse((self.root/'headless-receipts').exists())
    def test_supervisor_refuses_before_launch_for_yolo_and_non_yolo_parents(self):
        for yolo in ('1','0'):
            result=subprocess.run([sys.executable,str(ROOT/'hermes/headless/managed.py'),str(self.root),'18792'],
                input=json.dumps({'policy':{},'headless':self.settings})+'\n',text=True,capture_output=True,
                env=dict(os.environ,HERMES_YOLO_MODE=yolo),timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('child-only approval control',result.stderr)
            self.unchanged()
    def test_bridge_cli_refuses_resolve_and_submit_before_opening_config(self):
        # Missing config is deliberate: refusal must precede all file/network work.
        for op in ('resolve','submit'):
            result=subprocess.run([sys.executable,str(ROOT/'hermes/headless/bridge.py'),str(self.root/'missing.json')],
                input=json.dumps({'op':op,'target':'agent:main:saved'}),text=True,capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),dict(available=False,status='unavailable',reason=REASON))
            self.unchanged()
    def test_bridge_library_refuses_before_network_or_session_operations(self):
        instance=object.__new__(bridge.Bridge)
        with patch.object(bridge.httpx,'AsyncClient',side_effect=AssertionError('network attempted')) as client:
            with self.assertRaisesRegex(RuntimeError,REASON):asyncio.run(instance.run({'op':'submit'}))
            client.assert_not_called()
        self.unchanged()
    def test_saved_headless_setting_keeps_real_live_receiver_and_parent_policy(self):
        root=self.root/'s';root.mkdir(mode=0o700)
        bearer=self.root/'bearer';bearer.write_text('fixture-'*8);bearer.chmod(0o600)
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        # Stale/incomplete settings must not prevent the normal receiver starting.
        policy=dict(schemaVersion=2,receiver='test',bearerFile=str(bearer),mcs='off',inbox='on',peers={},destinations={},inboxFile=str(self.root/'inbox'),replayFile=str(self.root/'replay'),headless={'enabled':True})
        messages=[]
        class Ctx:
            def get_config(self,key,default=None):return policy.get(key,default)
            def inject_message(self,content,session_key):messages.append((content,session_key));return True
        ctx=Ctx()
        with patch.dict(os.environ,HERMES_YOLO_MODE='1',HERMES_HOME=str(self.home)):
            before=dict(os.environ)
            with self.assertLogs('hermes',level='WARNING') as logs:
                service=hermes.ReceiverService(root,port,ctx)
                listener=hermes.Listener(root,'agent:main:work','work',ctx)
                try:
                    deadline=time.monotonic()+5
                    while True:
                        try:urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/absent',timeout=.3)
                        except urllib.error.HTTPError as exc:
                            self.assertEqual(exc.code,404);exc.close();break
                        except OSError:
                            if time.monotonic()>deadline:self.fail('live receiver did not start')
                            time.sleep(.03)
                    with socket.socket(socket.AF_UNIX) as client:
                        client.settimeout(2);client.connect(str(listener.path))
                        client.sendall(json.dumps(dict(op='submit',target='agent:main:work',content='live fixture')).encode()+b'\n')
                        self.assertEqual(json.loads(client.recv(4096)),{'accepted':True})
                    self.assertEqual(messages,[('live fixture','work')])
                    self.assertEqual(before,dict(os.environ))
                finally:listener.close();service.close()
            self.assertTrue(any('headless unavailable' in line for line in logs.output))
        self.unchanged()

if __name__=='__main__':unittest.main()
