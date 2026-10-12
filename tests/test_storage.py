import importlib.util,json,os,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from contextlib import closing
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib'));sys.path.insert(0,str(ROOT/'hermes'))
import antenna_plugin_state as state
from profile_lock import ProfileLease
from storage import read_secret,data_directory
spec=importlib.util.spec_from_file_location('migration',ROOT/'scripts/antenna-storage.py')
migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
backup=migration.backup

class Storage(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);self.host=self.home/'config.yaml';self.old=self.home/'old-plugin';self.old.mkdir(mode=0o700)
        self.env=patch.dict(os.environ,{'PATH':str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH'],'HERMES_HOME':str(self.home)})
        self.env.start();self.addCleanup(self.env.stop)
        self.bearer='receiver-'+'x'*40
        self.write('secrets/self.token',self.bearer.encode())
        key=subprocess.check_output(['openssl','genpkey','-algorithm','ED25519'],stderr=subprocess.DEVNULL)
        pub=subprocess.run(['openssl','pkey','-pubout'],input=key,capture_output=True,check=True).stdout
        self.key=key;self.write('secrets/antenna-signing-private.pem',key);self.write('secrets/antenna-signing-public.pem',pub)
        self.write('antenna-config.json',state.encode(dict(transport_profile='antenna-plugin-v2',install_path=str(self.old),allowed_inbound_sessions=[],allowed_inbound_peers=[],allowed_outbound_peers=[],inbox_auto_approve_peers=[],inbox_enabled=True,inbox_mode='on',max_message_length=10000)))
        self.write('antenna-peers.json',state.encode({'self':dict(self=True,url='https://self.example',auth_mode='ed25519-v1',token_file='secrets/self.token',signing_private_key_file='secrets/antenna-signing-private.pem',signing_public_key_file='secrets/antenna-signing-public.pem')}))
        self.write('state/plugin-replay.json',state.encode({'entries':[dict(id='12345678-1234-4234-8234-123456789abc',peer='peer',seen=123)]}))
        socket=self.home/'s';socket.mkdir(mode=0o700)
        receipt=socket/'headless-receipts';receipt.mkdir(mode=0o700)
        with closing(sqlite3.connect(receipt/'receipts.sqlite')) as db:
            db.execute('create table receipts(peer text,mid text,digest text,target text,wirehash text,result text,primary key(peer,mid))')
            db.execute('insert into receipts values(?,?,?,?,?,?)',('peer','mid','digest','agent:main:work','original-hash','{"status":"unknown"}'))
            db.commit()
        (receipt/'receipts.sqlite').chmod(0o600)
        self.host.write_text(yaml.safe_dump({'unrelated':{'keep':'yes'},'plugins':{'enabled':[],'entries':{'antenna':{'settings':{'socket_dir':str(socket)},'config':dict(schemaVersion=2,receiver='self',bearer=self.bearer,mcs='off',inbox='on',peers={},destinations={},inboxFile=str(self.old/'state/plugin-inbox.json'),replayFile=str(self.old/'state/plugin-replay.json'))}}}}))
        self.host.chmod(0o600);state.HOST=self.host
    def write(self,name,raw):
        p=self.old/name;p.parent.mkdir(parents=True,exist_ok=True,mode=0o700);p.write_bytes(raw);p.chmod(0o600)
    def migrate(self):return migration.migrate(self.host,self.old)
    def test_migration_preserves_identity_replay_receipts_and_removal_retention(self):
        original=self.old.joinpath('antenna-peers.json').read_bytes();r=self.migrate();target=Path(r['dataRoot'])
        host,c=state.host_config()
        self.assertNotIn('bearer',c);self.assertNotIn(self.bearer,self.host.read_text())
        self.assertEqual(read_secret(c['bearerFile']),self.bearer)
        self.assertEqual((target/'secrets/antenna-signing-private.pem').read_bytes(),self.key)
        self.assertEqual((target/'state/plugin-replay.json').read_bytes(),(self.old/'state/plugin-replay.json').read_bytes())
        with closing(sqlite3.connect(c['receiptsFile'])) as db:self.assertEqual(db.execute('select wirehash from receipts').fetchone(),('original-hash',))
        self.assertEqual(host['unrelated'],{'keep':'yes'});self.assertEqual(host['plugins']['enabled'],[])
        self.assertEqual(self.old.joinpath('antenna-peers.json').read_bytes(),original)
        # Native removal targets only the install tree; data/identity stay outside it.
        self.old.rename(self.home/'removed-install');state.capture(target)
        self.assertTrue(migration.migrate(self.host,target)['alreadyCurrent'])
    def test_interrupted_copy_retry_preserves_identity_and_switches_only_after_copy(self):
        before=self.host.read_bytes();real=migration.backup.atomic;calls=[]
        def interrupted(path,raw):
            real(path,raw);calls.append(path)
            if len(calls)==2:raise OSError('simulated interruption')
        with patch.object(migration.backup,'atomic',side_effect=interrupted):
            with self.assertRaises(OSError):self.migrate()
        self.assertEqual(self.host.read_bytes(),before)
        self.migrate();self.assertEqual(read_secret(state.host_config()[1]['bearerFile']),self.bearer)
    def test_conflicting_target_fails_without_switch_or_overwrite(self):
        target=data_directory(self.host,create=True);p=target/'antenna-config.json';p.write_bytes(b'conflict');p.chmod(0o600)
        before=self.host.read_bytes()
        with self.assertRaises(state.StateError):self.migrate()
        self.assertEqual(self.host.read_bytes(),before);self.assertEqual(p.read_bytes(),b'conflict')
    def test_live_profile_and_unsafe_data_root_refused(self):
        before=self.host.read_bytes()
        with ProfileLease(self.home):
            with self.assertRaises(state.StateError):self.migrate()
        parent=self.home/'plugin-data';parent.mkdir(mode=0o700);(parent/'antenna').symlink_to(self.old)
        with self.assertRaises(ValueError):self.migrate()
        self.assertEqual(self.host.read_bytes(),before)
    def test_archive_roundtrip_restores_protected_bearer_not_yaml(self):
        target=Path(self.migrate()['dataRoot']);refs,files,_=state.capture(target)
        archive=self.home/'backup.tar';backup.write_archive(archive,target,files,refs)
        manifest,payload,fps=backup.load_archive(archive);self.assertIn('self',fps)
        plan,desired,prior,_,_,targets=backup.restore_plan(manifest,payload,target)
        with state.profile_operation():backup.replace_state(target,desired,prior,targets)
        self.assertNotIn(self.bearer,self.host.read_text());self.assertEqual(read_secret(state.host_config()[1]['bearerFile']),self.bearer)
        self.assertEqual(state.capture(target)[1],files)
    def test_consumers_use_migrated_storage_without_yaml_secret(self):
        target=Path(self.migrate()['dataRoot'])
        contact=self.home/'contact.json'
        commands=[['node','plugin/pairing.mjs','export',str(target),str(self.host),str(contact)],
                  ['node','plugin/cli.mjs',str(self.host),'mode','dumb'],
                  ['bash','bin/antenna.sh','config','show']]
        for command in commands:
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn(self.bearer,result.stdout+result.stderr)
        self.assertEqual(json.loads(contact.read_text())['antenna_bearer'],self.bearer)
        self.assertNotIn(self.bearer,self.host.read_text())
    def test_same_canonical_bearer_for_companion_and_receiver_is_supported(self):
        peers=state.decode((self.old/'antenna-peers.json').read_bytes());peers['self']['token_file']='secrets/receiver-bearer'
        self.write('antenna-peers.json',state.encode(peers));self.write('secrets/receiver-bearer',self.bearer.encode());(self.old/'secrets/self.token').unlink()
        target=Path(self.migrate()['dataRoot']);state.capture(target)
    def test_legacy_archive_conversion_and_private_secret_checks(self):
        refs,files,_=state.capture(self.old);archive=self.home/'old.tar'
        with patch.object(backup,'PRODUCER_VERSION','1.6.9'):backup.write_archive(archive,self.old,files,refs)
        m,payload,_=backup.load_archive(archive);target=data_directory(self.host)
        converted,_=backup.prepared(m,payload,target)
        self.assertNotIn('bearer',state.decode(converted[state.PLUGIN]))
        self.assertEqual(converted['secrets/receiver-bearer'].decode(),self.bearer)
        secret=self.old/'secrets/self.token';secret.chmod(0o644)
        with self.assertRaises(ValueError):read_secret(secret)
        secret.chmod(0o600);alias=secret.with_name('alias');alias.symlink_to(secret)
        with self.assertRaises(OSError):read_secret(alias)

if __name__=='__main__':unittest.main()
