import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

export function holdProfile(hostFile) {
 if(typeof hostFile!=='string'||!/\.ya?ml$/i.test(hostFile))throw Error('Hermes YAML host configuration required; foreign hosts are unsupported');
 const home=path.dirname(path.resolve(hostFile));
 const fd=Number(process.env.ANTENNA_PROFILE_LEASE_FD);
 if(process.env.ANTENNA_PROFILE_LEASE_HOME===home&&Number.isInteger(fd)&&fd>=3){
  try {
   const st=fs.fstatSync(fd),file=fs.lstatSync(path.join(home,'.antenna-profile.lock'));
   if(st.isFile()&&st.ino===file.ino&&st.dev===file.dev&&st.uid===process.getuid()&&!(st.mode&0o077)&&st.nlink===1)return;
  } catch { /* Missing inherited descriptor: acquire anew, never skip exclusion. */ }
 }
 const helper=fileURLToPath(new URL('../hermes/profile_lock.py',import.meta.url));
 const result=spawnSync('python3',[helper,home,'--',process.execPath,...process.execArgv,...process.argv.slice(1)],{stdio:'inherit'});
 if(result.error)throw Error('Profile lease helper unavailable');
 process.exit(result.status??1);
}

export function requireDataRoot(root,hostFile) {
 const expected=path.join(path.dirname(path.resolve(hostFile)),'plugin-data','antenna');
 if(path.resolve(root)!==expected||fs.realpathSync(root)!==expected)throw Error('Use the selected Hermes profile persistent Antenna data directory');
 const st=fs.lstatSync(root);
 if(!st.isDirectory()||st.uid!==process.getuid()||(st.mode&0o077))throw Error('Private owned Antenna data directory required');
}
