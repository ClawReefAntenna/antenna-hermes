#!/usr/bin/env python3
"""Explicit, stopped-profile, identity-preserving storage migration. Never starts services."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

CODE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CODE/'lib'))
import antenna_plugin_state as state
from storage import data_directory,private_directory
from receipt_store import snapshot_receipts
spec=importlib.util.spec_from_file_location('antenna_backup',CODE/'scripts/antenna-backup.py')
backup=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup)


def migrate(host,source):
    state.HOST=state.lexical(host);source=state.lexical(source)
    with state.profile_operation():
        state.quiescent()
        host_before=state.read_file(state.HOST,private=True)
        h,c=state.host_config()
        state.need('antenna' not in h['plugins'].get('enabled',[]),'ENABLED','Disable Antenna and stop its processes before migration.')
        target=data_directory(state.HOST)
        if source==target or (c.get('storageVersion')==1 and c.get('bearerFile')==str(target/'secrets/receiver-bearer')):
            state.need(c.get('storageVersion')==1 and 'bearer' not in c,'INVALID_STATE','Already-selected storage is not migrated.')
            state.capture(target)
            return {'migrated':True,'alreadyCurrent':True,'dataRoot':str(target)}
        refs,files,stamps=state.capture(source)
        # v1.6.9 receipts lived beside sockets and were not part of the companion inventory.
        old_receipts=Path(h['plugins']['entries']['antenna']['settings']['socket_dir'])/'headless-receipts/receipts.sqlite'
        if 'receiptsFile' not in c and old_receipts.exists():
            files[state.NATIVE['receiptsFile']]=snapshot_receipts(old_receipts)
        prepared,remaps=backup.prepared({'source_root':str(source)},files,target)
        policy=state.decode(prepared[state.PLUGIN]);policy['receiptsFile']=str(target/state.NATIVE['receiptsFile'])
        prepared[state.PLUGIN]=state.encode(policy)
        state.validate_snapshot(target,prepared)
        state.need(state.read_file(state.HOST,private=True)==host_before,'STATE_CHANGED','Host changed during migration.')
        target=data_directory(state.HOST,create=True)
        # Fail before publishing if an existing target differs. A killed pre-switch
        # migration can be retried: identical already-published files are accepted.
        payload={n:raw for n,raw in prepared.items() if n!=state.PLUGIN}
        for n,raw in payload.items():
            p=target/n;state.safe_path(p,missing=True,private=True)
            if p.exists():state.need(state.read_file(p,private=True)==raw,'TARGET_CONFLICT','Persistent data differs; migration will not overwrite it.')
        allowed=set(payload)
        for p in target.rglob('*'):
            state.need(p.is_dir() and not p.is_symlink() or p.relative_to(target).as_posix() in allowed,
                       'TARGET_CONFLICT','Unexpected persistent data; nothing overwritten.')
        for n,raw in payload.items():
            p=target/n
            for parent in reversed(p.relative_to(target).parents):
                if str(parent)!='.':private_directory(target/parent)
            if not p.exists():backup.atomic(p,raw)
        for n,raw in payload.items():state.need(state.read_file(target/n,private=True)==raw,'VERIFY_FAILED','Copied data differs.')
        # Recheck source under exclusion immediately before the only selection change.
        state.need(state.capture(source)[2]==stamps,'STATE_CHANGED','Source changed during migration.')
        h['plugins']['entries']['antenna']['config']=policy
        request=json.dumps({'original':host_before.decode(),'host':h}).encode()
        state.command([sys.executable,str(CODE/'hermes/host-config.py'),'save',str(state.HOST)],request)
        state.capture(target)
        return {'migrated':True,'dataRoot':str(target),'identity':'preserved','source':'retained','activation':'disabled','remappings':remaps}


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['migrate']);p.add_argument('--source',required=True)
    p.add_argument('--host',default=os.environ.get('ANTENNA_HOST_CONFIG',str(Path(os.environ.get('HERMES_HOME',str(Path.home()/'.hermes')))/'config.yaml')))
    a=p.parse_args();print(json.dumps(migrate(a.host,a.source)))

if __name__=='__main__':
    os.umask(0o077)
    try:main()
    except (state.StateError,ValueError,OSError,KeyError,TypeError):
        print('Storage migration refused or incomplete; keep Antenna disabled, inspect source/target permissions and retry. No source files were removed.',file=sys.stderr);sys.exit(1)
