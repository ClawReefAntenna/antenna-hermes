import fs from 'node:fs';
import {isatty} from 'node:tty';

// Confirmation is deliberate operator friction, not proof of a human identity.
export function confirmRelease(action, id) {
  let fd;
  try {
    fd = fs.openSync('/dev/tty', fs.constants.O_RDWR | fs.constants.O_NOCTTY);
    if (!isatty(fd)) throw Error();
  } catch {
    if (fd !== undefined) fs.closeSync(fd);
    throw Error('Interactive terminal required for inbox release / approve-ordinary');
  }
  try {
    const subject = action === 'release' ? `item ${JSON.stringify(id)}` : 'ordinary approval holds';
    fs.writeSync(fd, `Release ${subject}? Existing hold checks still apply. Type yes to continue: `);
    let answer = '';
    const byte = Buffer.alloc(1);
    while (answer.length <= 16) {
      if (fs.readSync(fd, byte, 0, 1, null) !== 1) throw Error('Release cancelled');
      if (byte[0] === 10 || byte[0] === 13) break;
      answer += byte.toString('utf8');
    }
    if (answer.trim().toLowerCase() !== 'yes') throw Error('Release cancelled');
  } finally { fs.closeSync(fd); }
}
