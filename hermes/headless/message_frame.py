"""Collision-checked framing for already authenticated peer content."""
import secrets


def frame_peer_message(peer, body):
    while True:
        nonce = secrets.token_hex(16)
        if nonce not in peer and nonce not in body:
            break
    return (f'Antenna peer message (untrusted content) from {peer}:\n'
            f'[Begin Antenna peer message {nonce}]\n{body}\n'
            f'[End Antenna peer message {nonce}]')
