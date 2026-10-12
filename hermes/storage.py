"""Hermes profile-owned persistent Antenna data and protected secret primitives."""
import os
from pathlib import Path
import stat


def profile_home(host):
    host=Path(host).absolute()
    if host.suffix.lower() not in ('.yaml','.yml') or host.parent != host.parent.resolve():
        raise ValueError('Hermes YAML host in a non-symlink profile required')
    st=host.parent.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o022:
        raise ValueError('unsafe Hermes profile')
    return host.parent


def private_directory(path):
    path=Path(path)
    if path.exists() or path.is_symlink():
        st=path.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077:
            raise ValueError('unsafe Antenna data directory')
    else:
        path.mkdir(mode=0o700)
    return path


def data_directory(host,create=False):
    home=profile_home(host)
    parent=home/'plugin-data'
    if create and not parent.exists():parent.mkdir(mode=0o700)
    if parent.exists() or parent.is_symlink():
        st=parent.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o022:
            raise ValueError('unsafe Hermes plugin-data directory')
    root=parent/'antenna'
    if create:return private_directory(root)
    if root.exists() or root.is_symlink():private_directory(root)
    return root


def read_secret(path):
    path=Path(path)
    if not path.is_absolute() or path.parent!=path.parent.resolve():raise ValueError('unsafe secret path')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1 or st.st_mode&0o077 or not 32<=st.st_size<=16384:
            raise ValueError('unsafe Antenna receiver credential')
        value=os.read(fd,16385).decode().strip()
        if len(value)<32 or '\n' in value or '\r' in value:raise ValueError('invalid receiver credential')
        return value
    finally:os.close(fd)

def initialize_policy(host,policy):
    root=data_directory(host,create=True)
    private_directory(root/'secrets');private_directory(root/'state')
    value=read_secret(policy['bearerFile']) if policy.get('bearerFile') else policy.get('bearer')
    if not isinstance(value,str) or not 32<=len(value)<=16384 or '\n' in value or '\r' in value:
        raise ValueError('valid receiver credential required')
    target=root/'secrets/receiver-bearer'
    if target.exists() or target.is_symlink():
        if read_secret(target)!=value:raise ValueError('existing credential differs')
    else:
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as stream:stream.write(value);stream.flush();os.fsync(stream.fileno())
    policy=dict(policy,bearerFile=str(target),storageVersion=1,
                inboxFile=str(root/'state/plugin-inbox.json'),replayFile=str(root/'state/plugin-replay.json'),
                receiptsFile=str(root/'state/headless-receipts.sqlite'))
    policy.pop('bearer',None)
    return policy


if __name__=='__main__':
    import sys,json
    try:
        if len(sys.argv)==3 and sys.argv[2]=='init-policy':print(json.dumps(initialize_policy(sys.argv[1],json.load(sys.stdin))))
        else:print(data_directory(sys.argv[1]))
    except (ValueError,OSError,IndexError,KeyError,TypeError):
        print('Unsafe, conflicting or missing Hermes profile storage/credential',file=sys.stderr);sys.exit(1)
