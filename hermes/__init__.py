"""Hermes adapter. Only public PluginContext APIs; no runtime imports or patches.

Prototype scope: already-started TUI/desktop sessions on Unix hosts. The owning
user is trusted; socket permissions separate other local users, not same-user code.
"""
import atexit
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import subprocess
import logging
import threading
import time
from .profile_lock import ProfileLease
from .storage import read_secret, private_directory as private_data_directory

MAX_FRAME = 4_004_096
POLICY_KEYS = ('schemaVersion', 'policyRevision', 'receiver', 'bearerFile', 'peers',
               'destinations', 'inboxFile', 'replayFile', 'mcs', 'inbox',
               'maxBodyChars', 'maxActiveSmart', 'scannerModel', 'scannerIdentity',
               'rulesetFile', 'receiptsFile', 'storageVersion')


class ReceiverService:
    """One loopback receiver shared by plugin processes using a private directory.

    The child inherits the kernel lease and watches its parent's pipe. Even if
    the parent crashes, the lease remains held until the child has shut down.
    Another loaded plugin can then take ownership. No message is retried.
    """
    def __init__(self, root, port, ctx, profile_lease=None):
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError('Antenna listen_port must be between 1024 and 65535')
        self.root, self.port, self.ctx = root, port, ctx
        self.profile_lease = profile_lease.retain() if profile_lease else None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True, name='antenna-receiver')
        try:self.thread.start()
        except BaseException:
            if self.profile_lease:self.profile_lease.close()
            raise

    def run(self):
        child = None
        scanner = None
        try:
            while not self.stop.is_set():
                lease = os.open(self.root / 'receiver.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                try:
                    try:
                        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        self.stop.wait(0.5)
                        continue
                    try:
                        scanner = SmartListener(self.root, 'antenna:scanner', None, self.ctx, self.profile_lease)
                    except BlockingIOError:
                        # A previous owner may still be finishing a host call.
                        self.stop.wait(0.5)
                        continue
                    policy = {k: self.ctx.get_config(k) for k in POLICY_KEYS if self.ctx.get_config(k) is not None}
                    if not policy.get('bearerFile'):
                        raise ValueError('Migrate Antenna storage before enabling v1.7.0')
                    policy['bearer']=read_secret(policy['bearerFile'])
                    headless = self.ctx.get_config('headless', {})
                    command = ['node', str(Path(__file__).with_name('receiver.mjs')), '--managed', str(self.root), str(self.port)]
                    payload = policy
                    if headless.get('enabled') is True:
                        command = [headless['python'], str(Path(__file__).parent/'headless/managed.py'), str(self.root), str(self.port)]
                        payload = {'policy': policy, 'headless': headless}
                    child = subprocess.Popen(
                        command,
                        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        pass_fds=(lease, self.profile_lease.fd) if self.profile_lease else (lease,),
                        env=dict(os.environ,ANTENNA_PROFILE_LEASE_FD=str(self.profile_lease.fd),
                                 ANTENNA_PROFILE_LEASE_HOME=str(self.profile_lease.path.parent)) if self.profile_lease else None, text=True)
                    child.stdin.write(json.dumps(payload) + '\n')
                    child.stdin.flush()
                finally:
                    os.close(lease)
                while not self.stop.wait(0.25):
                    if child.poll() is not None:
                        raise RuntimeError('receiver exited; check policy, Node and listen port, then reload plugin')
                break
        except Exception:
            logging.getLogger(__name__).error('Antenna receiver unavailable; check policy, Node and listen port, then reload plugin')
        finally:
            if scanner is not None:
                scanner.close()
            if child is not None:
                try:
                    child.stdin.close()  # EOF stops listener; bounded grace for in-flight requests.
                except OSError:
                    pass
                try:
                    child.wait(timeout=7)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            if self.profile_lease:
                self.profile_lease.close()


    def close(self):
        self.stop.set()
        self.thread.join(timeout=9)


def socket_path(directory, target):
    return Path(directory) / (hashlib.sha256(target.encode()).hexdigest()[:32] + '.sock')


def private_directory(value):
    root = Path(value)
    if not root.is_absolute():
        raise ValueError('Antenna socket directory must be absolute')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Antenna socket directory must be owned by this user and mode 0700')
    return root


class Listener:
    def __init__(self, root, target, session_key, ctx, profile_lease=None):
        self.target, self.session_key, self.ctx = target, session_key, ctx
        self.path = socket_path(root, target)
        if len(os.fsencode(self.path)) > 103:
            raise ValueError('Antenna socket directory path is too long')
        self.stop = threading.Event()
        self.lock = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if self.path.exists():
                if not stat.S_ISSOCK(self.path.lstat().st_mode):
                    raise ValueError('Unexpected file at Antenna socket path')
                self.path.unlink()  # lifetime lock proves no live adapter owns this stale socket
            self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server.bind(str(self.path))
            os.chmod(self.path, 0o600)
            self.inode = self.path.stat().st_ino
            self.server.listen(4)
            self.server.settimeout(0.25)
        except BaseException:
            os.close(self.lock)
            raise
        self.profile_lease = profile_lease.retain() if profile_lease else None
        self.thread = threading.Thread(target=self.run, daemon=True, name='antenna-session')
        try:self.thread.start()
        except BaseException:
            self.server.close();self.path.unlink(missing_ok=True);os.close(self.lock)
            if self.profile_lease:self.profile_lease.close()
            raise

    def run(self):
        while not self.stop.is_set():
            try:
                conn, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                conn.settimeout(2)
                try:
                    if hasattr(socket, 'SO_PEERCRED'):
                        _, uid, _ = struct.unpack('3i', conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                        if uid != os.getuid():
                            continue
                    raw = bytearray()
                    while b'\n' not in raw:
                        chunk = conn.recv(min(65536, MAX_FRAME + 1 - len(raw)))
                        if not chunk:
                            raise ValueError('Incomplete request')
                        raw.extend(chunk)
                        if len(raw) > MAX_FRAME:
                            raise ValueError('Oversized request')
                    request = json.loads(raw)
                    if set(request) - {'op', 'target', 'content'} or request.get('target') != self.target:
                        raise ValueError('Invalid target')
                    result = self.handle(request)
                    conn.sendall(json.dumps(result).encode() + b'\n')
                except Exception:
                    # No retry after an uncertain injection; caller reports unknown.
                    try:
                        conn.sendall(b'{"error":"adapter_request_failed"}\n')
                    except OSError:
                        pass

    def handle(self, request):
        if request.get('op') == 'resolve' and 'content' not in request:
            return {'available': True}
        if request.get('op') == 'submit' and isinstance(request.get('content'), str) and request['content'].strip():
            accepted = self.ctx.inject_message(request['content'], session_key=self.session_key)
            return {'accepted': accepted is True}
        raise ValueError('Invalid operation')

    def close(self):
        if self.stop.is_set():
            return
        self.stop.set()
        self.server.close()
        if threading.current_thread() is not self.thread:
            self.thread.join(timeout=3)
        def release():
            # A timed-out public host call may still be running. Retain its
            # lifetime lease until it actually ends; never overlap a replacement.
            if threading.current_thread() is not self.thread:
                self.thread.join()
            try:
                if self.path.lstat().st_ino == self.inode:
                    self.path.unlink()
            except FileNotFoundError:
                pass
            os.close(self.lock)
            if self.profile_lease:
                self.profile_lease.close()
        if self.thread.is_alive():
            threading.Thread(target=release, daemon=True, name='antenna-retire').start()
        else:
            release()


class SmartListener(Listener):
    """Serial out-of-band host calls; does not occupy session-injection sockets.

    A caller deadline holds the message, but cannot cancel Hermes's sync API.
    Keep this worker occupied until the host returns, preventing abandoned calls
    from creating unbounded provider concurrency. Expired queued calls never run.
    """
    def handle(self, request):
        content = request.get('content')
        if request.get('op') != 'scan' or not isinstance(content, dict):
            raise ValueError('Invalid scan')
        if len(json.dumps(content).encode()) > 20000:
            raise ValueError('Request budget')
        remaining = min(30, (content['deadlineAt'] - time.time() * 1000) / 1000)
        if remaining <= 0:
            raise ValueError('Expired scan')
        provider, model = content['model'].split('/', 1)
        if not provider or not model or not 1 <= content['maxTokens'] <= 1024:
            raise ValueError('Invalid selection or output bound')
        result = self.ctx.llm.complete(
            messages=[{'role':'system', 'content':content['systemPrompt']}, *content['messages']],
            provider=provider, model=model, max_tokens=content['maxTokens'],
            temperature=0, timeout=remaining, purpose='antenna.mcs')
        if time.time() * 1000 >= content['deadlineAt']:
            raise ValueError('Expired scan')
        if not isinstance(result.text, str) or len(result.text.encode()) > 65536:
            raise ValueError('Response budget')
        # Only public fields; no raw audit/auth/provider errors cross the socket.
        return {'text':result.text, 'provider':result.provider, 'model':result.model,
                'execution':{'mode':'hermes-plugin-llm'}}


def register(ctx):
    ctx.register_skill('antenna', Path(__file__).parent/'skills/antenna/SKILL.md',
                       'Send Antenna messages, inspect holds and run MCS diagnostics from Hermes.')
    # A fresh install may be inspected before setup (including by Plugin Doctor).
    # Missing configuration is inert, not permission to create storage or listen.
    # Explicit/partial configuration still goes through every normal guard below.
    missing = object()
    if all(ctx.get_config(key, missing) is missing for key in
           (*POLICY_KEYS, 'bearer', 'socket_dir', 'listen_port', 'agent_id', 'headless')):
        def inactive(**kwargs):
            return None
        for hook in ('on_session_start', 'on_session_finalize', 'on_session_reset', 'pre_llm_call'):
            ctx.register_hook(hook, inactive)
        logging.getLogger(__name__).warning(
            'Antenna is unconfigured and inactive; complete setup and reload before messaging.')
        return
    directory = ctx.get_config('socket_dir', None)
    root = private_directory(directory) if directory else None
    agent_id = ctx.get_config('agent_id', 'main')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', agent_id):
        raise ValueError('Invalid local agent id')
    listeners = {}
    guard = threading.RLock()
    port = ctx.get_config('listen_port', None)
    if port is not None and root is None:
        raise ValueError('Managed Antenna receiver requires a private socket_dir')
    # Public plugin storage API resolves the active Hermes profile. The lease
    # itself is outside the data tree so restore never replaces its inode.
    from plugins.plugin_storage import plugin_data_dir
    data_root = private_data_directory(Path(plugin_data_dir('antenna')))
    profile_home = data_root.parent.parent
    profile_lease = ProfileLease(profile_home)
    try:
        for field,relative in {'bearerFile':'secrets/receiver-bearer','inboxFile':'state/plugin-inbox.json',
                               'replayFile':'state/plugin-replay.json','receiptsFile':'state/headless-receipts.sqlite'}.items():
            if ctx.get_config(field)!=str(data_root/relative):
                raise ValueError('Migrate Antenna to profile-owned persistent storage before enabling')
        if ctx.get_config('headless',{}).get('enabled') is True and Path(ctx.get_config('headless')['home'])!=profile_home:
            raise ValueError('Headless home must match the owning Hermes profile')
    except BaseException:
        profile_lease.close();raise
    try:
        service = ReceiverService(root, port, ctx, profile_lease) if port is not None and os.environ.get('ANTENNA_HEADLESS_CHILD') != '1' else None
    except BaseException:
        profile_lease.close();raise

    def on_start(session_id, platform='', **kwargs):
        # CLI injection ignores the requested key; do not advertise false exact-session support.
        if root is None or platform not in ('tui', 'desktop') or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', session_id):
            return
        with guard:
            if session_id not in listeners:
                target = f'agent:{agent_id}:{session_id}'
                listeners[session_id] = Listener(root, target, session_id, ctx, profile_lease)

    def on_finalize(session_id=None, **kwargs):
        with guard:
            listener = listeners.pop(session_id, None)
        if listener:
            listener.close()

    closed = False
    def close():
        nonlocal closed
        if closed:
            return
        closed = True
        if service:
            service.close()
        with guard:
            current = list(listeners.values())
            listeners.clear()
        for listener in current:
            listener.close()
        profile_lease.close()

    ctx.register_hook('on_session_start', on_start)
    ctx.register_hook('on_session_finalize', on_finalize)
    ctx.register_hook('on_session_reset', on_finalize)
    # Resume can reuse a cached system prompt without firing on_session_start.
    ctx.register_hook('pre_llm_call', on_start)
    ctx.on_unload(close)
    atexit.register(close)
