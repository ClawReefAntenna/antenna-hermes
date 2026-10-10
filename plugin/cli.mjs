#!/usr/bin/env node
import {LIMITS} from './limits.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {loadHost} from './host-config.mjs';
import {validateConfig,modes} from './policy.mjs';
import {resolveScanner,gatewayScan} from './smart.mjs';
import {loadRuleset} from './ruleset.mjs';
import {Inbox} from './inbox.mjs';
const args=process.argv.slice(2),configPath=args.shift(),command=args.shift();
const help='Usage: antenna-plugin <host-config> status|init <policy.json>|mode <off|dumb|smart|both> [peer]|check <registered-model-or-alias>|select <registered-model-or-alias>|rules validate|select <absolute-file>|inbox list|show|release|discard|approve-ordinary [id] [acknowledgements JSON]';
try{
 if(!configPath||!command)throw Error(help);
 if(command==='mcs')throw Error('Use the separate Antenna Diagnostics Kit for Hermes: node diagnostics/cli.mjs CONFIG_YAML test|evaluate ...');
 if(command==='migrate')throw Error('Use separate Antenna Migration for Hermes: node migration/cli.mjs CONFIG_YAML [NEW_POLICY_JSON | --apply]');
 const storage=loadHost(configPath),{original,host,runtime}=storage;
 const hermes=runtime==='hermes'?await import('../hermes/smart.mjs'):null;
 const resolveModel=hermes?.resolveHermesScanner??resolveScanner,scanModel=hermes?.hermesScan??gatewayScan;
 const notice=hermes?.NOTICE;
 const entry=host.plugins?.entries?.antenna;
 let c=entry?.config;
 function save(next){
  const validated=validateConfig(next,{requireReady:true,host,resolveModel});
  if(runtime==='hermes'){
   const copy=structuredClone(host);copy.plugins??={};copy.plugins.entries??={};
   copy.plugins.entries.antenna={...(copy.plugins.entries.antenna??{}),config:validated};
   // Native Hermes activation is plugins.enabled; initialization never enables it.
   if(!entry&&(host.plugins?.enabled??[]).includes('antenna'))throw Error('Disable Antenna before initialization');
   storage.save(copy);
   console.log(JSON.stringify({saved:true,restartRequired:true,activation:'unchanged',...(notice?{notice}: {})}));return;
  }
  if(fs.readFileSync(configPath,'utf8')!==original)throw Error('configuration changed; reload before editing');
  const lock=configPath+'.antenna-lock';fs.mkdirSync(lock,{mode:0o700});
  const tmp=configPath+'.'+randomUUID()+'.tmp';
  try{
   if(fs.readFileSync(configPath,'utf8')!==original)throw Error('configuration changed');
   const copy=structuredClone(host);copy.plugins??={};copy.plugins.entries??={};
   copy.plugins.entries.antenna={...(copy.plugins.entries.antenna??{enabled:false}),config:validated};
   const fd=fs.openSync(tmp,'wx',0o600);
   try{fs.writeFileSync(fd,JSON.stringify(copy,null,2)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
   fs.renameSync(tmp,configPath);
   const dir=fs.openSync(path.dirname(path.resolve(configPath)),'r');try{fs.fsyncSync(dir);}finally{fs.closeSync(dir);}
  }finally{if(fs.existsSync(tmp))fs.unlinkSync(tmp);fs.rmdirSync(lock);}
  console.log(JSON.stringify({saved:true,restartRequired:true,activation:'unchanged',...(notice?{notice}: {})}));
 }
 if(command==='init'){
  if(entry)throw Error('Antenna entry exists; use mode/select or explicit migration');
  save(JSON.parse(fs.readFileSync(args[0],'utf8')));
 }else{
  c=validateConfig(c);
  if(command==='status'){
   let p;try{p=resolveModel(c.scannerModel,host);}catch{}
   const items=new Inbox(c.inboxFile,{readOnly:true}).read().items;
   const stateCounts=Object.fromEntries(['scanning','held','dispatching','submitted','unknown','discarded'].map(state=>[state,items.filter(r=>r.state===state).length]));
   console.log(JSON.stringify({stateCounts,...(notice?{notice}:{}),limits:LIMITS,maxActiveSmart:c.maxActiveSmart,schemaVersion:2,mcs:c.mcs,inbox:c.inbox,peers:Object.fromEntries(Object.entries(c.peers).map(([k,v])=>[k,{configured:v.mcs??'default',effective:!v.mcs||v.mcs==='default'?c.mcs:v.mcs}])),scanner:p?{model:p.model,modelId:p.modelId,ready:p.identity===c.scannerIdentity}:null,ruleset:{file:c.rulesetFile??'bundled',hash:loadRuleset(c.rulesetFile).hash}}));
  }else if(command==='mode'){
   const [mode,peer]=args;
   if(!modes.includes(mode)&&!(peer&&mode==='default'))throw Error('invalid mode');
   if(peer){if(!Object.hasOwn(c.peers,peer))throw Error('unknown peer');c.peers[peer].mcs=mode;}else c.mcs=mode;
   save(c);
  }else if(command==='rules'){
   const [action,file]=args;if(!['validate','select'].includes(action)||!file)throw Error('rules validate|select /absolute/file.json');
   const rules=loadRuleset(file);
   if(action==='select'){c.rulesetFile=file;save(c);}else console.log(JSON.stringify({valid:true,rules:rules.rules.length,hash:rules.hash,qualityAccepted:false}));
  }else if(command==='check'||command==='select'){
   if(notice)console.error(notice);
   const p=resolveModel(args[0],host);
   const result=await scanModel(host,p,'Please review tomorrow’s meeting agenda.');
   if(result.verdict!=='pass')throw Error('scanner compatibility check failed: '+(result.reason??result.verdict));
   if(command==='select'){delete c.scannerProfile;c.scannerModel=p.model;c.scannerIdentity=p.identity;save(c);}
   else console.log(JSON.stringify({compatible:true,model:p.modelId,qualityAccepted:false,activated:false,...(notice?{notice,returnedModel:result.returnedModel}: {})}));
  }else if(command==='inbox'){
   const [action,id,ack='[]']=args,inbox=new Inbox(c.inboxFile);
   if(action==='list')console.log(JSON.stringify(inbox.read().items.map(r=>({id:r.id,state:r.state,reasons:r.reasons}))));
   else if(action==='show')console.log(JSON.stringify(inbox.get(id))); // JSON escaping keeps controls inert.
   else if(action==='discard')console.log(JSON.stringify({state:inbox.discard(id).state}));
   else{
    // Do not recover state in a second operator process while the gateway scans.
    const delivery=await import(runtime==='hermes'?'../hermes/receiver.mjs':'./runtime.mjs');
    const options=runtime==='hermes'?delivery.managedOptions(entry.settings?.socket_dir,entry.settings?.headless??c.headless):{};
    const flow=delivery.makeFlow(c,runtime==='hermes'?entry.settings?.socket_dir:host,options);
    let result;
    if(action==='release')result=await flow.release(id,JSON.parse(ack));
    else if(action==='approve-ordinary')result=await flow.approveOrdinary();
    else throw Error('unknown inbox action');
    console.log(JSON.stringify(result));
   }
  }else throw Error(help);
 }
}catch(e){console.error(JSON.stringify({status:'error',reason:e instanceof SyntaxError?'invalid JSON input':e.message}));process.exitCode=1;}
