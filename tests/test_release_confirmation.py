import fcntl,json,os,pty,select,subprocess,sys,tempfile,termios,time,unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]

class ReleaseConfirmation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.socket=self.root/'s';self.socket.mkdir(mode=0o700)
        self.inbox=self.root/'state/inbox.json';self.host=self.root/'config.yaml'
        c=dict(schemaVersion=2,receiver='self',bearer='x'*40,mcs='off',inbox='on',peers={},destinations={},
               inboxFile=str(self.inbox),replayFile=str(self.root/'state/replay.json'))
        self.host.write_text(yaml.safe_dump({'plugins':{'entries':{'antenna':{'config':c,'settings':{'socket_dir':str(self.socket)}}}}}));self.host.chmod(0o600)
        self.env={**os.environ,'PATH':str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH']}
    def args(self,action):return ['node','plugin/cli.mjs',str(self.host),'inbox',action,'fixture-id','[]']
    def test_noninteractive_both_release_commands_refuse_without_state_write(self):
        for action in ('release','approve-ordinary'):
            r=subprocess.run(self.args(action),cwd=ROOT,env=self.env,input='yes\n',capture_output=True,text=True,start_new_session=True,timeout=5)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('Interactive terminal required',r.stderr)
            self.assertFalse(self.inbox.parent.exists())
    def terminal_run(self,action,answer):
        master,slave=pty.openpty()
        def session():os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
        p=subprocess.Popen(self.args(action),cwd=ROOT,env=self.env,stdin=slave,stdout=slave,stderr=slave,preexec_fn=session)
        os.close(slave);output=b''
        try:
            deadline=time.monotonic()+5
            while b'Type yes to continue:' not in output:
                if time.monotonic()>deadline:raise AssertionError(output)
                if select.select([master],[],[],.1)[0]:output+=os.read(master,4096)
            os.write(master,answer)
            while p.poll() is None:
                if time.monotonic()>deadline:raise AssertionError(output)
                if select.select([master],[],[],.1)[0]:
                    try:output+=os.read(master,4096)
                    except OSError:break
            p.wait(timeout=3)
            return p.returncode,output.decode(errors='replace')
        finally:
            if p.poll() is None:p.kill();p.wait()
            os.close(master)
    def test_refusal_and_eof_do_not_create_or_mutate_inbox(self):
        for action in ('release','approve-ordinary'):
            for answer in (b'no\n',b'\x04'):
                code,output=self.terminal_run(action,answer)
                self.assertNotEqual(code,0,output)
                self.assertFalse(self.inbox.parent.exists())
    def test_confirmation_allows_existing_ordinary_release_flow(self):
        code,output=self.terminal_run('approve-ordinary',b'yes\n')
        self.assertEqual(code,0,output)
        self.assertTrue(self.inbox.parent.exists())
        self.assertFalse(self.inbox.exists()) # no held items; no fabricated delivery
    def test_confirmation_does_not_bypass_existing_item_checks(self):
        code,output=self.terminal_run('release',b'yes\n')
        self.assertNotEqual(code,0,output)
        self.assertIn('item not found',output)
        self.assertFalse(self.inbox.exists())

if __name__=='__main__':unittest.main()
