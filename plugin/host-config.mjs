// Hermes-only native host serialization. Refuse foreign paths before reading.
import {holdProfile} from './profile-lease.mjs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
export function loadHost(file){
 if(typeof file!=='string'||!/\.ya?ml$/i.test(file))throw Error('Hermes YAML host configuration required; foreign hosts are unsupported');
 holdProfile(file);
 const helper=fileURLToPath(new URL('../hermes/host-config.py',import.meta.url));
 const invoke=(action,input)=>{
  const result=spawnSync('python3',[helper,action,file],{input:JSON.stringify(input),encoding:'utf8',maxBuffer:8*1024*1024});
  if(result.status!==0)throw Error('Hermes configuration '+action+' failed: '+(result.stderr?.trim()||'helper unavailable'));
  return JSON.parse(result.stdout);
 };
 const {original,host}=invoke('snapshot',{});
 return {original,host,runtime:'hermes',save:host=>invoke('save',{original,host})};
}
