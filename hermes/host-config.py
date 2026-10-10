"""Atomic native YAML operator writes; never guesses a profile or reads OpenClaw.

PyYAML is supplied by Hermes. Unknown host settings are preserved semantically.
Comments/formatting are normalized on writes, as with the JSON host operator.
"""
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import yaml


def private_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('host config must be an owned, private regular file')


def main():
    action, name = sys.argv[1:]
    path = Path(name).absolute()
    private_file(path)
    request = json.load(sys.stdin)
    if action == 'read':
        host = yaml.safe_load(path.read_text())
        if not isinstance(host, dict):
            raise ValueError('host config must be a mapping')
        print(json.dumps(host))
        return
    if action != 'save':
        raise ValueError('unknown operation')
    lock = os.open(str(path) + '.antenna-lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        private_file(path)
        if path.read_text() != request['original']:
            raise ValueError('configuration changed; reload before editing')
        payload = yaml.safe_dump(request['host'], sort_keys=False)
        fd, temporary = tempfile.mkstemp(prefix='.antenna-', dir=path.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    finally:
        os.close(lock)
    print('{"saved":true}')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Parser errors may quote secret-bearing source lines. Do not echo them.
        print('invalid, unsafe, busy or changed host configuration', file=sys.stderr)
        sys.exit(1)
