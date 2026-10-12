# Retained Antenna headless regression harness, now targeting this candidate.
import sys
from pathlib import Path
HEADLESS=Path(__file__).resolve().parents[1]/'hermes/headless'
sys.path.insert(0,str(HEADLESS))
"""Supervisor lifecycle tests with an authenticated fake public backend."""
import json,os,socket,subprocess,sys,tempfile,time,unittest,urllib.request
from pathlib import Path
import managed
HERE=HEADLESS
class Managed(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.home=self.root/'home';self.home.mkdir()
        self.cfg=self.home/'config.yaml';self.cfg.write_text('desktop: {auto_continue: {enabled: false}}')
        self.backend=self.root/'hermes'
        self.backend.write_text('''#!/usr/bin/env python3
import http.server,os,sys,json
from pathlib import Path
Path(os.environ['HERMES_HOME'],'backend-pid').write_text(str(os.getpid()))
class H(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200 if self.headers.get('Authorization')=='Bearer '+os.environ['HERMES_DASHBOARD_SESSION_TOKEN'] else 401);self.end_headers();self.wfile.write(b'[]')
 def log_message(self,*args):pass
http.server.HTTPServer(('127.0.0.1',int(sys.argv[sys.argv.index('--port')+1])),H).serve_forever()
''');self.backend.chmod(0o700)
        def port():
            with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
        self.port=port();self.settings=dict(enabled=True,python=sys.executable,hermes=str(self.backend),home=str(self.home),port=port(),grants={'sender':['agent:main:stored']})
        self.policy=dict(schemaVersion=2,receiver='test',bearer='test-bearer-'*5,mcs='off',inbox='off',peers={},destinations={},inboxFile=str(self.root/'inbox'),replayFile=str(self.root/'replay'))
        self.child=None
    def tearDown(self):
        if self.child and self.child.poll() is None:self.child.stdin.close();self.child.wait(timeout=7)
        if self.child:
            for stream in (self.child.stdin,self.child.stdout,self.child.stderr):
                if stream:stream.close()
        self.tmp.cleanup()
    def start(self):
        self.child=subprocess.Popen([sys.executable,str(HERE/'managed.py'),str(self.root),str(self.port)],stdin=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.child.stdin.write(json.dumps({'policy':self.policy,'headless':self.settings})+'\n');self.child.stdin.flush()
    def ready(self):
        deadline=time.monotonic()+6
        while time.monotonic()<deadline:
            try:
                urllib.request.urlopen('http://127.0.0.1:'+str(self.port)+'/absent')
            except urllib.error.HTTPError as e:
                code=e.code;e.close()
                if code==404:return
            except OSError:pass
            if self.child.poll() is not None:self.fail(self.child.stderr.read())
            time.sleep(.05)
        self.fail('not ready')
    def stopped(self):
        self.child.wait(timeout=7)
        pid=int((self.home/'backend-pid').read_text())
        with self.assertRaises(ProcessLookupError):os.kill(pid,0)
        self.assertEqual(list(self.root.glob('headless-*/token')),[])
        self.assertTrue((self.root/'headless-receipts').is_dir())
    def test_parent_eof_stops_backend_receiver_and_removes_credentials(self):
        self.start();self.ready();self.child.stdin.close();self.stopped()
    def test_signal_stops_children(self):
        self.start();self.ready();self.child.terminate();self.stopped()
    def test_backend_exit_stops_receiver(self):
        self.start();self.ready();os.kill(int((self.home/'backend-pid').read_text()),15);self.stopped()
    def test_continuation_policy_is_owned_by_hermes(self):
        for cfg in ('{}', 'desktop: {auto_continue: {enabled: true}}', 'desktop: {auto_continue: {enabled: false}}'):
            self.cfg.write_text(cfg)
            managed.validate(self.settings)
            self.assertEqual(self.cfg.read_text(),cfg)
        self.cfg.unlink()
        managed.validate(self.settings)  # Hermes owns defaults and config loading.
    def test_default_off_and_relative_path_refused(self):
        with self.assertRaises(ValueError):managed.validate({**self.settings,'enabled':False})
        with self.assertRaises(ValueError):managed.validate({**self.settings,'home':'relative'})
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Managed))
    sys.exit(not result.wasSuccessful())
