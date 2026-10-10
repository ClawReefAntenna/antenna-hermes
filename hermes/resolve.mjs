// Existing exact-session listeners only. No history/private host tables or creation.
import fs from 'node:fs';
import {loadHost} from '../plugin/host-config.mjs';
import {makeAdapter,socketPath} from './adapter.mjs';
try {
 const [file,key]=process.argv.slice(2),{host,runtime}=loadHost(file);
 if(runtime!=='hermes'||!/^agent:[A-Za-z0-9_-]+:[A-Za-z0-9_-]+$/.test(key))throw Error();
 const directory=host.plugins?.entries?.antenna?.settings?.socket_dir;
 const adapter=makeAdapter(directory),socket=socketPath(directory,key);
 try {fs.lstatSync(socket);}catch(e){if(e.code==='ENOENT'){console.log(JSON.stringify({ok:true,key:null}));process.exit(0);}throw e;}
 if(!await adapter.resolve(key))throw Error();
 console.log(JSON.stringify({ok:true,key,agentId:key.split(':')[1]}));
}catch {console.error('Hermes exact-session resolver unavailable');process.exitCode=1;}
