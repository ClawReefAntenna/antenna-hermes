#!/usr/bin/env node
import {loadHost} from './host-config.mjs';
import {operatorAuth} from './operator-auth.mjs';
import {hooksWarning} from './migration-warning.mjs';
import {resolveScanner} from './smart.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {validateConfig} from './policy.mjs';
import {PROFILE} from './transport.mjs';
try{
 const [command,file,root]=process.argv.slice(2),read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
 if(command==='sources'){
  const report=read(file),changed=Object.entries(report.sourceHashes).filter(([p,h])=>!fs.existsSync(p)||createHash('sha256').update(fs.readFileSync(p)).digest('hex')!==h).map(([p])=>p);
  console.log(JSON.stringify({unchanged:changed.length===0,changed}));if(changed.length)process.exitCode=1;
 }else if(command==='doctor'){
  const {host,runtime}=loadHost(file),old=read(path.join(root,'antenna-config.json')),peers=read(path.join(root,'antenna-peers.json'));
  const c=validateConfig(host.plugins?.entries?.antenna?.config),self=Object.values(peers).filter(p=>p.self===true);
  if(self.length!==1)throw Error('ambiguous retained identity');
  const legacyBearer=fs.readFileSync(path.resolve(root,self[0].token_file),'utf8').trim(),problems=[];
  if(old.transport_profile!==PROFILE)problems.push('legacy send/writer controls not switched');
  if(runtime==='hermes'?!host.plugins?.enabled?.includes('antenna'):(!host.plugins?.entries?.antenna?.enabled||(host.plugins?.allow?.length&&!host.plugins.allow.includes('antenna'))||host.plugins?.deny?.includes('antenna')))problems.push('plugin disabled or not allowlisted');
  const warnings=runtime==='hermes'||host.hooks?.enabled===false?[]:[hooksWarning];
  if(runtime==='openclaw'){try{operatorAuth(host,[legacyBearer,c.bearer]);}catch{problems.push('operator credential separation not established');}}
  else {
   if(!peers[c.receiver]?.self)problems.push('Hermes receiver differs from companion identity');
   const settings=host.plugins.entries.antenna.settings??{};
   if(!path.isAbsolute(settings.socket_dir??'')||!Number.isInteger(settings.listen_port)||settings.listen_port<1024||settings.listen_port>65535)problems.push('Hermes receiver settings missing or invalid');
   if(typeof settings.socket_dir==='string'&&Buffer.byteLength(path.join(settings.socket_dir,'0'.repeat(32)+'.sock'))>103)problems.push('Hermes socket directory path is too long');
   try{const st=fs.lstatSync(settings.socket_dir);if(!st.isDirectory()||st.uid!==process.getuid()||(st.mode&0o077))throw Error();}catch{problems.push('Hermes socket directory missing or unsafe');}
  }
  const relay=old.relay_agent_id??'antenna';
  if(host.agents?.list?.some(a=>a.id===relay)||Object.hasOwn(host.agents?.entries??{},relay))problems.push('legacy relay agent still provisioned; review ownership before removal');
  if(host.hooks?.mappings?.some(m=>JSON.stringify(m).includes('antenna')))problems.push('possible old Antenna mapping remains; review manually');
  if([c.mcs,...Object.values(c.peers).map(p=>p.mcs)].some(m=>['smart','both'].includes(m))){try{if((runtime==='hermes'?(await import('../hermes/smart.mjs')).resolveHermesScanner:resolveScanner)(c.scannerModel,host).identity!==c.scannerIdentity)throw Error();}catch{problems.push('registered scanner selection not validated');}}
  console.log(JSON.stringify({staticChecksPassed:problems.length===0,liveIngressVerified:false,problems,warnings,runtime,required:runtime==='hermes'?'After stopping/reloading all profile processes, verify signed admission, exact-session delivery and peer denials; static checks do not prove HTTPS exposure.':'After explicit restart, verify signed plugin admission and denial of operator access using peer credentials. If hooks were rotated or disabled, also verify old hook access is denied; otherwise retained hook access is outside Antenna checks.'}));if(problems.length)process.exitCode=1;
 }else throw Error('sources REPORT | doctor HOST LEGACY_ROOT');
}catch(e){console.error(JSON.stringify({status:'blocked',reason:e.message}));process.exitCode=1;}
