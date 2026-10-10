// Native host serialization only. Antenna's schema-2 policy stays unchanged.
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
export function loadHost(file){
 const original=fs.readFileSync(file,'utf8');
 if(!/\.ya?ml$/i.test(file))return {original,host:JSON.parse(original),runtime:'openclaw'};
 const helper=fileURLToPath(new URL('../hermes/host-config.py',import.meta.url));
 const invoke=(action,input)=>{
  const result=spawnSync('python3',[helper,action,file],{input:JSON.stringify(input),encoding:'utf8',maxBuffer:8*1024*1024});
  if(result.status!==0)throw Error('Hermes configuration '+action+' failed: '+(result.stderr?.trim()||'helper unavailable'));
  return JSON.parse(result.stdout);
 };
 return {original,host:invoke('read',{}),runtime:'hermes',save:host=>invoke('save',{original,host})};
}
