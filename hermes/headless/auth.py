"""Public dashboard login/ticket client. No runtime imports or gate exemptions."""
import fcntl,json,os,stat
from pathlib import Path

def private_json(path):
    p=Path(path);s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077:raise ValueError('private auth file required')
    return json.loads(p.read_text())

async def authenticate(http,config):
    response=await http.get('/api/sessions')
    if response.status_code==200:return False
    response.raise_for_status() if response.status_code!=401 else None
    if not config.get('login_file'):response.raise_for_status()
    # A stale bearer takes precedence over valid cookies in the gated middleware.
    http.headers.pop('Authorization',None)
    login=private_json(config['login_file']);cache=Path(config['cookie_file'])
    fd=os.open(str(cache)+'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX)
        if cache.exists():http.cookies.update(private_json(cache))
        response=await http.get('/api/sessions')
        if response.status_code==200:return True
        if response.status_code!=401:response.raise_for_status()
        http.cookies.clear()
        response=await http.post('/auth/password-login',json={'provider':'basic',**login})
        response.raise_for_status()
        response=await http.get('/api/sessions');response.raise_for_status()
        temp=cache.with_suffix('.new');out=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(out,'w') as stream:json.dump(dict(http.cookies),stream)
        os.replace(temp,cache)
        return True
    finally:os.close(fd)

async def websocket_query(http,token,gated):
    from urllib.parse import quote
    if not gated:return 'token='+quote(token,safe='')
    response=await http.post('/api/auth/ws-ticket');response.raise_for_status()
    return 'ticket='+quote(response.json()['ticket'],safe='')
