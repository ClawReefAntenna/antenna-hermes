#!/usr/bin/env node
import {requireDataRoot} from './profile-lease.mjs';
import {loadHost} from './host-config.mjs';
import {resolveHermesScanner} from '../hermes/smart.mjs';
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
  const {host,runtime}=loadHost(file);requireDataRoot(root,file);
  const old=read(path.join(root,'antenna-config.json')),peers=read(path.join(root,'antenna-peers.json'));
  const c=validateConfig(host.plugins?.entries?.antenna?.config),self=Object.values(peers).filter(p=>p.self===true);
  if(self.length!==1)throw Error('ambiguous retained identity');
  const problems=[];
  if(!c.bearerFile||Object.hasOwn(host.plugins.entries.antenna.config,'bearer')||c.storageVersion!==1)problems.push('receiver storage migration required');
  for(const [field,relative] of Object.entries({bearerFile:'secrets/receiver-bearer',inboxFile:'state/plugin-inbox.json',replayFile:'state/plugin-replay.json',receiptsFile:'state/headless-receipts.sqlite'}))
   if(c[field]!==path.join(root,relative))problems.push('noncanonical persistent '+field);
  if(old.transport_profile!==PROFILE)problems.push('legacy send/writer controls not switched');
  if(!host.plugins?.enabled?.includes('antenna'))problems.push('plugin disabled');
  const warnings=[];
  {
   if(!peers[c.receiver]?.self)problems.push('Hermes receiver differs from companion identity');
   const settings=host.plugins.entries.antenna.settings??{};
   if(!path.isAbsolute(settings.socket_dir??'')||!Number.isInteger(settings.listen_port)||settings.listen_port<1024||settings.listen_port>65535)problems.push('Hermes receiver settings missing or invalid');
   if(typeof settings.socket_dir==='string'&&Buffer.byteLength(path.join(settings.socket_dir,'0'.repeat(32)+'.sock'))>103)problems.push('Hermes socket directory path is too long');
   try{const st=fs.lstatSync(settings.socket_dir);if(!st.isDirectory()||st.uid!==process.getuid()||(st.mode&0o077))throw Error();}catch{problems.push('Hermes socket directory missing or unsafe');}
  }
  if([c.mcs,...Object.values(c.peers).map(p=>p.mcs)].some(m=>['smart','both'].includes(m))){try{if(resolveHermesScanner(c.scannerModel,host).identity!==c.scannerIdentity)throw Error();}catch{problems.push('registered scanner selection not validated');}}
  console.log(JSON.stringify({staticChecksPassed:problems.length===0,liveIngressVerified:false,problems,warnings,runtime,required:'After stopping/reloading all profile processes, verify signed admission, exact-session delivery and peer denials; static checks do not prove HTTPS exposure.'}));if(problems.length)process.exitCode=1;
 }else throw Error('sources REPORT | doctor HOST LEGACY_ROOT');
}catch(e){console.error(JSON.stringify({status:'blocked',reason:e.message}));process.exitCode=1;}
