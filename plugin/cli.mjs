#!/usr/bin/env node
import {LIMITS} from './limits.mjs';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {loadHost} from './host-config.mjs';
import {validateConfig,modes} from './policy.mjs';
import {resolveHermesScanner,hermesScan,NOTICE} from '../hermes/smart.mjs';
import {loadRuleset} from './ruleset.mjs';
import {Inbox} from './inbox.mjs';
import {storedPolicy} from './secret-file.mjs';
import {confirmRelease} from './confirm-release.mjs';
const args=process.argv.slice(2),configPath=args.shift(),command=args.shift();
const help='Usage: antenna-plugin <host-config> status|init <policy.json>|mode <off|dumb|smart|both> [peer]|check <registered-model-or-alias>|select <registered-model-or-alias>|rules validate|select <absolute-file>|inbox list|show|release|discard|approve-ordinary [id] [acknowledgements JSON]';
try{
 if(!configPath||!command)throw Error(help);
 if(command==='mcs')throw Error('Use the separate Antenna Diagnostics Kit for Hermes: node diagnostics/cli.mjs CONFIG_YAML test|evaluate ...');
 if(command==='migrate')throw Error('Use separate Antenna Migration for Hermes: node migration/cli.mjs CONFIG_YAML [NEW_POLICY_JSON | --apply]');
 const storage=loadHost(configPath),{original,host,runtime}=storage;
 const resolveModel=resolveHermesScanner,scanModel=hermesScan;
 const notice=NOTICE;
 const entry=host.plugins?.entries?.antenna;
 let c=entry?.config;
 function save(next){
  const validated=validateConfig(next,{requireReady:true,host,resolveModel});
  const copy=structuredClone(host);copy.plugins??={};copy.plugins.entries??={};
  copy.plugins.entries.antenna={...(copy.plugins.entries.antenna??{}),config:storedPolicy(validated)};
  if(!entry&&(host.plugins?.enabled??[]).includes('antenna'))throw Error('Disable Antenna before initialization');
  storage.save(copy);
  console.log(JSON.stringify({saved:true,restartRequired:true,activation:'unchanged',notice}));
 }
 if(command==='init'){
  if(entry)throw Error('Antenna entry exists; use mode/select or explicit migration');
  const input=JSON.parse(fs.readFileSync(args[0],'utf8'));
  validateConfig(input,{requireReady:true,host,resolveModel});
  const prepared=spawnSync('python3',[fileURLToPath(new URL('../hermes/storage.py',import.meta.url)),configPath,'init-policy'],{input:JSON.stringify(input),encoding:'utf8'});
  if(prepared.status!==0)throw Error('Protected storage initialization failed');
  save(JSON.parse(prepared.stdout));
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
   const [action,id,ack='[]']=args;
   if(!['list','show','discard','release','approve-ordinary'].includes(action))throw Error('unknown inbox action');
   if(['release','approve-ordinary'].includes(action))confirmRelease(action,id);
   const inbox=new Inbox(c.inboxFile);
   if(action==='list')console.log(JSON.stringify(inbox.read().items.map(r=>({id:r.id,state:r.state,reasons:r.reasons}))));
   else if(action==='show')console.log(JSON.stringify(inbox.get(id))); // JSON escaping keeps controls inert.
   else if(action==='discard')console.log(JSON.stringify({state:inbox.discard(id).state}));
   else{
    // Do not recover state in a second operator process while the gateway scans.
    const delivery=await import('../hermes/receiver.mjs');
    const options=delivery.managedOptions(entry.settings?.socket_dir,entry.settings?.headless??c.headless);
    const flow=delivery.makeFlow(c,entry.settings?.socket_dir,options);
    let result;
    if(action==='release')result=await flow.release(id,JSON.parse(ack));
    else if(action==='approve-ordinary')result=await flow.approveOrdinary();
    else throw Error('unknown inbox action');
    console.log(JSON.stringify(result));
   }
  }else throw Error(help);
 }
}catch(e){console.error(JSON.stringify({status:'error',reason:e instanceof SyntaxError?'invalid JSON input':e.message}));process.exitCode=1;}
