"""Transactional native canary installer. Review staged config before --apply.
Stops specified service writers before snapshot/install; restores local state
before activation. Any failure restores original plugin/config then services.
This does not send messages or alter the staged continuation/auth policy.
"""
import argparse,os,shutil,subprocess,time
from pathlib import Path


def restore_local(old,new,source):
    count=0
    for p in old.rglob('*'):
        rel=p.relative_to(old)
        if any(x in ('.git','__pycache__') for x in rel.parts) or p.suffix=='.pyc':continue
        if p.is_symlink():raise ValueError('Review local symlink before deployment: '+str(rel))
        if not p.is_file() or (source/rel).exists():continue
        # Native installer owns its provenance metadata, not the backup.
        if rel.name.startswith('.hermes-plugin'):continue
        out=new/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
        if out.read_bytes()!=p.read_bytes():raise RuntimeError('Local state restore failed')
        count+=1
    return count


def deploy(home,source,staged,hermes,units,run=subprocess.run):
    env=dict(os.environ,HERMES_HOME=str(home))
    def command(args):return run(args,env=env,check=True)
    live=home/'plugins/antenna';original=(home/'config.yaml').read_bytes();planned=staged.read_bytes()
    rollback=home/'antenna-canary'/('transaction-'+time.strftime('%Y%m%d-%H%M%S'))
    rollback.mkdir(mode=0o700,parents=True,exist_ok=False)
    command(['systemctl','--user','stop',*units])
    saved=False
    try:
        (rollback/'config.yaml').write_bytes(original);(rollback/'config.yaml').chmod(0o600)
        shutil.copytree(live,rollback/'antenna',symlinks=True);saved=True
        command([str(hermes),'plugins','install',source.as_uri(),'--no-enable','--force'])
        restore_local(rollback/'antenna',live,source)
        for p in source.rglob('*'):
            if not p.is_file() or '.git' in p.relative_to(source).parts:continue
            if (live/p.relative_to(source)).read_bytes()!=p.read_bytes():raise RuntimeError('Installed source mismatch')
        tmp=home/'config.canary-new';tmp.write_bytes(planned);tmp.chmod(0o600);os.replace(tmp,home/'config.yaml')
        command(['systemctl','--user','start',*units])
    except BaseException:
        if saved:
            if live.exists():os.rename(live,rollback/'failed-install')
            shutil.copytree(rollback/'antenna',live,symlinks=True)
            (home/'config.yaml').write_bytes(original);(home/'config.yaml').chmod(0o600)
        command(['systemctl','--user','start',*units])
        raise
    return rollback

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('home','source','staged','hermes'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--unit',action='append',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--allow-scan-override',action='store_true');a=p.parse_args()
    if not a.apply or not a.allow_scan_override:p.error('Explicit --apply and authorized --allow-scan-override required')
    for v in (a.home,a.source,a.staged,a.hermes):
        if not v.is_absolute():p.error('Absolute paths required')
    print('Rollback:',deploy(a.home,a.source,a.staged,a.hermes,a.unit))
