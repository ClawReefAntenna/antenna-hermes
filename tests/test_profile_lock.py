import importlib,json,os,signal,socket,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'hermes'))
from profile_lock import ProfileLease,ProfileBusy

class ProfileLocks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
    def test_active_and_standby_shared_owners_exclude_recovery(self):
        first=ProfileLease(self.home);second=ProfileLease(self.home)
        try:
            with self.assertRaises(ProfileBusy):ProfileLease(self.home,exclusive=True)
            first.close()
            with self.assertRaises(ProfileBusy):ProfileLease(self.home,exclusive=True)
        finally: first.close();second.close()
        with ProfileLease(self.home,exclusive=True):pass
    def test_recovery_excludes_startup_and_other_profiles_remain_independent(self):
        other=self.home/'other';other.mkdir(mode=0o700)
        with ProfileLease(self.home,exclusive=True):
            with self.assertRaises(ProfileBusy):ProfileLease(self.home)
            with ProfileLease(other):pass
        with ProfileLease(self.home):pass
    def test_reference_retained_for_inflight_worker(self):
        lease=ProfileLease(self.home);lease.retain();lease.close()
        with self.assertRaises(ProfileBusy):ProfileLease(self.home,exclusive=True)
        lease.close()
        with ProfileLease(self.home,exclusive=True):pass
    def test_inherited_child_lease_survives_parent_descriptor_close(self):
        lease=ProfileLease(self.home)
        child=subprocess.Popen([sys.executable,'-c','import sys; print("ready",flush=True);sys.stdin.read()'],
                               stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,pass_fds=(lease.fd,))
        try:
            self.assertEqual(child.stdout.readline().strip(),'ready')
            lease.close()
            with self.assertRaises(ProfileBusy):ProfileLease(self.home,exclusive=True)
            child.stdin.close();child.wait(timeout=3)
            with ProfileLease(self.home,exclusive=True):pass
        finally:
            lease.close()
            if child.poll() is None:child.kill();child.wait()
            child.stdout.close()
    def test_stale_file_is_not_busy_but_symlink_hardlink_and_loose_mode_are_refused(self):
        with ProfileLease(self.home):pass
        lock=self.home/'.antenna-profile.lock'
        with ProfileLease(self.home,exclusive=True):pass
        lock.chmod(0o644)
        with self.assertRaises(ValueError):ProfileLease(self.home)
        lock.chmod(0o600)
        alias=self.home/'alias';os.link(lock,alias)
        with self.assertRaises(ValueError):ProfileLease(self.home)
        alias.unlink();lock.unlink();lock.symlink_to(self.home/'missing')
        with self.assertRaises(OSError):ProfileLease(self.home)
    def test_real_cli_writer_blocked_during_recovery(self):
        host=self.home/'config.yaml';host.write_text('plugins: {enabled: []}\n');host.chmod(0o600)
        before=host.read_bytes()
        env={**os.environ,'PATH':str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH']}
        with ProfileLease(self.home,exclusive=True):
            result=subprocess.run(['node','plugin/cli.mjs',str(host),'init','missing-policy.json'],
                                  cwd=ROOT,env=env,text=True,capture_output=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('profile is busy',result.stderr)
            self.assertEqual(before,host.read_bytes())
    def test_real_receiver_survives_owner_crash_with_profile_lease(self):
        root=self.home/'s';root.mkdir(mode=0o700)
        bearer=self.home/'bearer';bearer.write_text('fixture-'*8);bearer.chmod(0o600)
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        policy=dict(schemaVersion=2,receiver='test',bearerFile=str(bearer),mcs='off',inbox='on',peers={},destinations={},inboxFile=str(self.home/'inbox'),replayFile=str(self.home/'replay'))
        script="""import json,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from hermes import ReceiverService
from hermes.profile_lock import ProfileLease
class Ctx:
 def get_config(self,k,default=None):return policy.get(k,default)
policy=json.loads(sys.argv[4]);lease=ProfileLease(Path(sys.argv[2]).parent)
service=ReceiverService(Path(sys.argv[2]),int(sys.argv[3]),Ctx(),lease)
print('owner-ready',flush=True)
sys.stdin.read()
service.close();lease.close()
"""
        owner=subprocess.Popen([sys.executable,'-c',script,str(ROOT),str(root),str(port),json.dumps(policy)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        child=None
        try:
            self.assertEqual(owner.stdout.readline().strip(),'owner-ready')
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                children=[]
                for child_file in Path('/proc/'+str(owner.pid)+'/task').glob('*/children'):
                    try:children.extend(child_file.read_text().split())
                    except FileNotFoundError:pass
                if children:child=int(children[0]);break
                time.sleep(.02)
            self.assertIsNotNone(child)
            os.kill(child,signal.SIGSTOP);owner.kill();owner.wait(timeout=3)
            with self.assertRaises(ProfileBusy):ProfileLease(self.home,exclusive=True)
            os.kill(child,signal.SIGCONT)
            deadline=time.monotonic()+8
            while True:
                try:
                    with ProfileLease(self.home,exclusive=True):break
                except ProfileBusy:
                    if time.monotonic()>deadline:raise
                    time.sleep(.03)
        finally:
            if owner.poll() is None:owner.kill();owner.wait()
            if child:
                try:os.kill(child,signal.SIGKILL)
                except ProcessLookupError:pass
            for stream in (owner.stdin,owner.stdout,owner.stderr):stream.close()
    def test_listener_retains_lease_until_inflight_host_call_finishes(self):
        import hermes
        root=self.home/'s';root.mkdir(mode=0o700)
        started=threading.Event();finish=threading.Event()
        class Ctx:
            def inject_message(self,*args,**kwargs):started.set();finish.wait(10);return True
        lease=ProfileLease(self.home)
        listener=hermes.Listener(root,'agent:main:work','work',Ctx(),lease)
        client=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            client.connect(str(listener.path));client.sendall(json.dumps(dict(op='submit',target='agent:main:work',content='fixture')).encode()+b'\n')
            self.assertTrue(started.wait(2));listener.close();lease.close()
            with self.assertRaises(ProfileBusy):ProfileLease(self.home,exclusive=True)
            finish.set();listener.thread.join(timeout=3)
            deadline=time.monotonic()+2
            while True:
                try:
                    with ProfileLease(self.home,exclusive=True):break
                except ProfileBusy:
                    if time.monotonic()>deadline:raise
                    time.sleep(.02)
        finally:
            finish.set();client.close();listener.close();lease.close()

if __name__=='__main__':unittest.main()
