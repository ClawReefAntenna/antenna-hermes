// Development receiver: shared 1.6.8 ingress and policy; Hermes-local delivery.
// Loopback only. Production setup/service/HTTPS integration remains unimplemented.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import readline from 'node:readline';
import {fileURLToPath} from 'node:url';
import {validateConfig} from '../plugin/policy.mjs';
import {authenticate} from '../plugin/envelope.mjs';
import {Inbox,ReceiveFlow} from '../plugin/inbox.mjs';
import {createReceiver} from '../plugin/receive.mjs';
import {loadRuleset} from '../plugin/ruleset.mjs';
import {scanDumb} from '../plugin/scanners.mjs';
import {capacityDirectory} from '../plugin/capacity.mjs';
import {makeAdapter} from './adapter.mjs';
import {makeHeadlessAdapter} from './headless/adapter.mjs';
import {makeHermesSmart} from './smart.mjs';
// Owner-local inbox release must use the same managed delivery mode as ingress.
export function managedOptions(directory,settings){
 if(settings?.enabled!==true)return {};
 const file=path.join(directory,'headless-active.json'),stat=fs.lstatSync(file);
 if(!stat.isFile()||stat.uid!==process.getuid()||(stat.mode&0o077))throw Error('managed backend unavailable');
 const headless=JSON.parse(fs.readFileSync(file,'utf8'));
 if(headless.python!==settings.python||!headless.config.startsWith(path.resolve(directory)+path.sep))throw Error('managed backend mismatch');
 return {headless};
}
export function makeFlow(config,directory,options={}){
 const c=validateConfig(config),adapter=options.headless?makeHeadlessAdapter(options.headless):makeAdapter(directory),ruleset=loadRuleset(c.rulesetFile);
 const flow=new ReceiveFlow({inbox:new Inbox(c.inboxFile),authorize:fields=>authenticate(fields,c,Date.parse(fields.timestamp)),...adapter,smart:makeHermesSmart(c,directory),
  dumb:body=>scanDumb(body,{ruleset,resourceDir:capacityDirectory(path.dirname(c.inboxFile))})});
 return flow;
}
export function receiver(config,directory,options={}){
 const c=validateConfig(config),adapter=options.headless?makeHeadlessAdapter(options.headless):makeAdapter(directory),flow=makeFlow(c,directory,options);
 flow.inbox.recover();
 const handler=createReceiver({config:c,flow,resolve:adapter.resolve});
 return http.createServer((req,res)=>{if(req.url!=='/antenna/v1/receive'){res.writeHead(404);res.end();return;}handler(req,res);});
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [file,directory,port='0']=process.argv.slice(2);
 if(file==='--managed'){
  // Private anonymous parent pipe, not an argument/env value or temporary secret file.
  const lines=readline.createInterface({input:process.stdin});
  let server,started=false;
  const stop=()=>{if(server)server.close(()=>process.exit(0));else process.exit(0);setTimeout(()=>process.exit(0),6000).unref();};
  lines.on('line',line=>{
   if(started)return;started=true;
   try{const payload=JSON.parse(line);server=receiver(payload.managed_policy??payload,directory,payload.managed_policy?{headless:payload.headless}:{});server.on('error',()=>process.exit(1));server.listen(Number(port),'127.0.0.1');}
   catch{process.exit(1);}
  });
  lines.on('close',stop);
  for(const signal of ['SIGINT','SIGTERM'])process.on(signal,stop);
 }else{
 const stat=fs.lstatSync(file);if(!stat.isFile()||stat.uid!==process.getuid()||(stat.mode&0o077))throw Error('private policy file required');
 const server=receiver(JSON.parse(fs.readFileSync(file,'utf8')),directory);
 server.listen(Number(port),'127.0.0.1',()=>console.log(JSON.stringify({port:server.address().port})));
 for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>server.close(()=>process.exit(0)));
 }
}
