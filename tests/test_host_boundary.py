import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib'))
import antenna_plugin_state as state
import session_policy

class HostBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.env={**os.environ,'HOME':str(self.home),'HERMES_HOME':str(self.home/'hermes'),
                  'PATH':str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH']}
        self.foreign=self.home/'openclaw.json'
        self.foreign.write_text('{"gateway":{"auth":{"token":"foreign-sentinel"}}}')
        self.foreign.chmod(0o600)
        self.initial=self.foreign.read_bytes()
    def run_cli(self,*args):
        return subprocess.run(args,cwd=ROOT,env=self.env,capture_output=True,text=True,timeout=10)
    def test_node_refuses_foreign_before_file_read(self):
        script="""import fs from 'node:fs'; import {loadHost} from './plugin/host-config.mjs';
fs.readFileSync=()=>{throw Error('READ-WAS-ATTEMPTED');};
try {loadHost('/nonexistent/openclaw.json');process.exit(2);} catch(e) {
if(!e.message.includes('foreign hosts are unsupported')) throw e;
} """
        r=self.run_cli('node','--input-type=module','-e',script)
        self.assertEqual(r.returncode,0,r.stderr)
    def test_host_consumers_refuse_foreign_configs(self):
        for command in [('node','plugin/cli.mjs',str(self.foreign),'status'),
                        ('node','plugin/migration-check.mjs','doctor',str(self.foreign),str(self.home)),
                        (sys.executable,'hermes/host-config.py','read',str(self.foreign)),
                        (sys.executable,'scripts/antenna-backup.py','inspect','unused.age','--host',str(self.foreign))]:
            r=self.run_cli(*command)
            self.assertNotEqual(r.returncode,0,command)
            self.assertNotIn('foreign-sentinel',r.stdout+r.stderr)
        self.assertEqual(self.foreign.read_bytes(),self.initial)
    def test_python_state_and_resolver_refuse_before_foreign_access(self):
        state.HOST=self.foreign
        with patch.object(state,'read_file',side_effect=AssertionError('read forbidden')):
            with self.assertRaises(state.StateError):state.host_config()
        with patch.dict(os.environ,{'ANTENNA_HOST_CONFIG':str(self.foreign)}),patch.object(session_policy.subprocess,'run',side_effect=AssertionError('spawn forbidden')):
            with self.assertRaises(session_policy.PolicyError):session_policy.gateway({'key':'agent:main:work'})
    def test_direct_legacy_admin_cannot_restart_or_edit_foreign_host(self):
        bindir=self.home/'bin';bindir.mkdir();marker=self.home/'invoked'
        fake=bindir/'openclaw';fake.write_text('#!/bin/sh\ntouch '+str(marker)+'\n');fake.chmod(0o700)
        self.env['PATH']=str(bindir)+os.pathsep+self.env['PATH']
        for args in [('model','set','anything'),('setup',),('upgrade',),('uninstall',),('peers','exchange')]:
            r=self.run_cli('bash','bin/antenna-companion.sh',*args)
            self.assertNotEqual(r.returncode,0)
        self.assertFalse(marker.exists())
        self.assertEqual(self.foreign.read_bytes(),self.initial)
    def test_valid_hermes_init_and_status_preserve_unrelated_settings(self):
        host=self.home/'config.yaml';host.write_text('plugins: {enabled: []}\nunrelated: keep-me\n');host.chmod(0o600)
        policy=self.home/'policy.json';policy.write_text(json.dumps(dict(schemaVersion=2,receiver='self',bearer='x'*40,
            mcs='off',inbox='on',peers={},destinations={},inboxFile=str(self.home/'inbox.json'),replayFile=str(self.home/'replay.json'))))
        r=self.run_cli('node','plugin/cli.mjs',str(host),'init',str(policy));self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('keep-me',host.read_text())
        self.assertNotIn('x'*40,host.read_text())
        self.assertIn('bearerFile:',host.read_text())
        r=self.run_cli('node','plugin/cli.mjs',str(host),'status');self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['inbox'],'on')
        self.assertNotIn('x'*40,r.stdout)
    def test_yaml_symlink_to_foreign_config_refused(self):
        alias=self.home/'config.yaml';alias.symlink_to(self.foreign)
        r=self.run_cli('node','plugin/cli.mjs',str(alias),'status')
        self.assertNotEqual(r.returncode,0)
        self.assertNotIn('foreign-sentinel',r.stderr+r.stdout)

if __name__=='__main__': unittest.main()
