import {randomBytes} from 'node:crypto';

// Render only after envelope authentication. Never change the signed body.
export function framePeerMessage(peer, body) {
  let nonce;
  do { nonce = randomBytes(16).toString('hex'); }
  while (peer.includes(nonce) || body.includes(nonce));
  return `Antenna peer message (untrusted content) from ${peer}:\n` +
    `[Begin Antenna peer message ${nonce}]\n${body}\n` +
    `[End Antenna peer message ${nonce}]`;
}
