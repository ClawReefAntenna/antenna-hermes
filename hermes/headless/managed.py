"""Plugin-owned supervisor; public Hermes CLI only. Parent EOF revokes service.

The receiver lease stays inherited here until both children have stopped. Secret
files are ephemeral; durable receipts are outside the temporary credential folder.
"""
import asyncio,json,os,secrets,selectors,signal,stat,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
import httpx
from auth import authenticate
from availability import require_headless_control


def child_environment(parent,settings,token,password):
    # Parent/session bypass flags never become child launch authority. Explicit
    # false prevents fallback-only env sources from filling a missing value.
    env={k:v for k,v in parent.items() if not k.startswith('HERMES_SESSION_') and k not in (
        'HERMES_YOLO_MODE','HERMES_PROFILE','HERMES_INTERACTIVE','HERMES_SINGLE_QUERY_SESSION',
        'HERMES_CRON_SESSION','HERMES_ACP_AUTO_APPROVE')}
    env.update(HERMES_HOME=settings['home'],HERMES_YOLO_MODE='0',
               HERMES_DASHBOARD_SESSION_TOKEN=token,ANTENNA_HEADLESS_CHILD='1',
               HERMES_DASHBOARD_BASIC_AUTH_USERNAME='antenna-private',
               HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=password,
               HERMES_DASHBOARD_BASIC_AUTH_SECRET=secrets.token_urlsafe(48))
    return env


def validate(settings):
    if settings.get('enabled') is not True: raise ValueError('headless must be explicit')
    for key in ('python','hermes','home'):
        if not Path(settings[key]).is_absolute(): raise ValueError('absolute paths required')
    if type(settings.get('port')) is not int or not 1024<=settings['port']<=65535: raise ValueError('invalid backend port')
    if not isinstance(settings.get('grants'),dict) or not settings['grants']: raise ValueError('explicit grants required')


def terminate(child):
    if child is None:return
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=1.5)
    except subprocess.TimeoutExpired:
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        child.wait()


def main():
    require_headless_control()  # Before input, credentials, state or child launch.
    os.umask(0o077)
    request=json.loads(sys.stdin.readline());settings=request['headless'];validate(settings)
    root=Path(sys.argv[1]);port=int(sys.argv[2]);receipt=request['policy'].get('receiptsFile')
    state=Path(receipt).parent if receipt else root/'headless-receipts'
    if not state.is_absolute():raise ValueError('absolute receipt directory required')
    state.mkdir(mode=0o700,exist_ok=True)
    info=state.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:raise ValueError('private state directory required')
    monitor=selectors.DefaultSelector();monitor.register(sys.stdin,selectors.EVENT_READ)
    profile_fd=int(os.environ['ANTENNA_PROFILE_LEASE_FD']) if 'ANTENNA_PROFILE_LEASE_FD' in os.environ else None
    profile_fds=(profile_fd,) if profile_fd is not None else ()
    if profile_fd is not None: os.fstat(profile_fd)
    backend=receiver=None
    active=root/'headless-active.json'
    def interrupted(*_):raise SystemExit(0)
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,interrupted)
    try:
        with tempfile.TemporaryDirectory(prefix='headless-',dir=root) as temporary:
            folder=Path(temporary);token=secrets.token_urlsafe(48)
            tokenfile=folder/'token';tokenfile.write_text(token)
            password=secrets.token_urlsafe(48)
            loginfile=folder/'login.json';loginfile.write_text(json.dumps({'username':'antenna-private','password':password}))
            origin='http://127.0.0.1:'+str(settings['port'])
            config=folder/'bridge.json';config.write_text(json.dumps(dict(origin=origin,token_file=str(tokenfile),state_dir=str(state),receipt_file=receipt or str(state/'receipts.sqlite'),agent_id=settings.get('agent_id','main'),grants=settings['grants'],login_file=str(loginfile),cookie_file=str(folder/'cookies.json'))))
            env=child_environment(os.environ,settings,token,password)
            backend=subprocess.Popen([settings['hermes'],'serve','--isolated','--host','127.0.0.1','--port',str(settings['port']),'--skip-build'],env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,pass_fds=profile_fds)
            deadline=time.monotonic()+60
            while True:
                if monitor.select(.1):return
                if backend.poll() is not None:raise RuntimeError('backend exited')
                try:
                    async def ready():
                        async with httpx.AsyncClient(base_url=origin,headers={'Authorization':'Bearer '+token},trust_env=False,timeout=2) as http:
                            await authenticate(http,json.loads(config.read_text()))
                    asyncio.run(ready())
                    break
                except Exception:
                    if time.monotonic()>deadline:raise RuntimeError('backend readiness failed')
            pointer=folder/'active.json'
            pointer.write_text(json.dumps({'python':settings['python'],'config':str(config)}))
            os.replace(pointer,active)
            receiver=subprocess.Popen(['node',str(Path(__file__).parents[1]/'receiver.mjs'),'--managed',str(root),str(port)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True,start_new_session=True,pass_fds=profile_fds)
            receiver.stdin.write(json.dumps({'managed_policy':request['policy'],'headless':{'python':settings['python'],'config':str(config)}})+'\n');receiver.stdin.flush()
            while not monitor.select(.1):
                if backend.poll() is not None or receiver.poll() is not None:raise RuntimeError('managed child exited')
            # Stop while files still exist for any already admitted request.
            terminate(receiver);receiver=None
            terminate(backend);backend=None
    finally:
        # Ignore a second termination signal during bounded cleanup.
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        terminate(receiver);terminate(backend);active.unlink(missing_ok=True);monitor.close()

if __name__=='__main__':
    try:main()
    except BaseException:
        print('Antenna headless unavailable: a supported Hermes child-only approval control is required; use a live session',file=sys.stderr)
        sys.exit(1)
