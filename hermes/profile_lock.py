"""Profile-wide cooperative lifetime lock, outside replaceable plugin/state trees.

Close descriptors, never explicitly unlock: managed children inherit the same
open file description and must keep the lease when their parent dies.
"""
import fcntl
import os
from pathlib import Path
import stat
import threading


class ProfileBusy(RuntimeError):
    pass


class ProfileLease:
    def __init__(self, home, exclusive=False):
        home = Path(home)
        if not home.is_absolute() or home != home.resolve():
            raise ValueError('absolute, non-symlink Hermes profile required')
        info = home.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError('unsafe Hermes profile directory')
        self.path = home / '.antenna-profile.lock'
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o077:
                raise ValueError('unsafe Antenna profile lock')
            try:
                fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ProfileBusy('Antenna profile is active or backup/restore is in progress') from None
        except BaseException:
            os.close(fd)
            raise
        self.fd = fd
        self._references = 1
        self._guard = threading.Lock()

    def retain(self):
        with self._guard:
            if self._references == 0:
                raise RuntimeError('profile lease already closed')
            self._references += 1
        return self

    def close(self):
        with self._guard:
            if self._references == 0:
                return
            self._references -= 1
            if self._references == 0:
                os.close(self.fd)

    def __enter__(self): return self
    def __exit__(self, *_): self.close()


def exec_with_lease(home, command):
    """Exec a local CLI writer with an inherited shared lease."""
    lease = ProfileLease(home)
    os.set_inheritable(lease.fd, True)
    env = dict(os.environ, ANTENNA_PROFILE_LEASE_FD=str(lease.fd),
               ANTENNA_PROFILE_LEASE_HOME=str(lease.path.parent))
    try: os.execvpe(command[0], command, env)
    finally: lease.close()


if __name__ == '__main__':
    import sys
    try:
        home, separator, *command = sys.argv[1:]
        if separator != '--' or not command:
            raise ValueError('profile home and command required')
        exec_with_lease(home, command)
    except Exception:
        print('Antenna profile is busy, unsafe, or unavailable; no operation performed.', file=sys.stderr)
        sys.exit(1)
