import fs from 'node:fs';
import path from 'node:path';
export function readReceiverBearer(file) {
 if(typeof file!=='string'||!path.isAbsolute(file)||fs.realpathSync(path.dirname(file))!==path.dirname(file))throw Error('absolute, non-symlink bearer file required');
 const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
 try {
  const st=fs.fstatSync(fd);
  if(!st.isFile()||st.uid!==process.getuid()||(st.mode&0o077)||st.nlink!==1||st.size<32||st.size>16384)throw Error('private owned bearer file required');
  const value=fs.readFileSync(fd,'utf8').trim();
  if(value.length<32||/[\r\n]/.test(value))throw Error('invalid receiver bearer');
  return value;
 } finally { fs.closeSync(fd); }
}
export function storedPolicy(config) {
 const c=structuredClone(config);
 if(!c.bearerFile)throw Error('Migrate Antenna storage before changing this policy');
 delete c.bearer;
 return c;
}
