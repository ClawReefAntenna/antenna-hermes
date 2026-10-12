"""Offline bounded receipt snapshots, retaining unknown-delivery reconciliation."""
from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile


def validate_receipts(raw):
    with tempfile.TemporaryDirectory(prefix='antenna-receipts-') as folder:
        file=Path(folder)/'receipts.sqlite';file.write_bytes(raw);file.chmod(0o600)
        with closing(sqlite3.connect(file.as_uri()+'?mode=ro',uri=True)) as db:
            if db.execute('pragma integrity_check').fetchall()!=[('ok',)]:raise ValueError('invalid receipts')
            if [row[1] for row in db.execute('pragma table_info(receipts)')]!=['peer','mid','digest','target','wirehash','result']:
                raise ValueError('invalid receipt schema')


def snapshot_receipts(file):
    # Caller owns the profile exclusive lease and has checked legacy writers.
    from antenna_state import safe_path
    safe_path(file,private=True)
    for suffix in ('-wal','-shm'):
        safe_path(Path(str(file)+suffix),missing=True,private=True)
    with tempfile.TemporaryDirectory(prefix='antenna-receipts-') as folder:
        target=Path(folder)/'receipts.sqlite'
        with closing(sqlite3.connect(file.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
        raw=target.read_bytes();validate_receipts(raw);return raw
