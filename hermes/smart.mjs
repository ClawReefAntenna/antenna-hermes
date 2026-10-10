// Public Hermes completion bridge. Credentials and fallback stay host-owned.
import net from 'node:net';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {socketPath,makeAdapter} from './adapter.mjs';
import {createSmart} from '../plugin/smart.mjs';
import {LIMITS} from '../plugin/limits.mjs';
import {capacityDirectory} from '../plugin/capacity.mjs';
export const NOTICE='Preferred scanning model: Hermes may retry or use a fallback model if this model is unavailable. Fallback follows your Hermes configuration and may use a different provider.';
export function resolveHermesScanner(model,host){
 if(typeof model!=='string'||! /^[a-zA-Z0-9_-]+\/[^\s@]+$/.test(model))throw Error('select a Hermes provider/model (provider followed by the full model ID)');
 const slash=model.indexOf('/'),provider=model.slice(0,slash),id=model.slice(slash+1);
 if(host){
  const policy=host.plugins?.entries?.antenna?.llm??{};
  for(const [type,value] of [['provider',provider],['model',id]]){
   const list=policy['allowed_'+type+'s'];
   if(policy['allow_'+type+'_override']!==true||Array.isArray(list)&&!list.includes('*')&&!list.includes(value))throw Error('Hermes native LLM trust settings must allow the selected '+type+'; configure plugins.entries.antenna.llm and reload');
  }
 }
 return {model,modelId:model,identity:createHash('sha256').update(JSON.stringify(['hermes-host-fallback-v1',model])).digest('hex')};
}
export function hermesCompletion(directory){
 makeAdapter(directory); // Enforce the same private-directory boundary as delivery.
 return args=>new Promise((resolve,reject)=>{
  const deadlineAt=Date.now()+args.execution.timeoutMs;
  const socket=net.createConnection(socketPath(directory,'antenna:scanner'));socket.setEncoding('utf8');let raw='',done=false;
  const finish=(error,value)=>{if(done)return;done=true;clearTimeout(timer);args.signal?.removeEventListener('abort',abort);socket.destroy();error?reject(error):resolve(value);};
  const abort=()=>finish(Error('scanner_timeout'));
  const timer=setTimeout(abort,args.execution.timeoutMs);
  if(args.signal?.aborted){abort();return;}args.signal?.addEventListener('abort',abort,{once:true});
  socket.on('connect',()=>socket.write(JSON.stringify({op:'scan',target:'antenna:scanner',content:{model:args.model,systemPrompt:args.systemPrompt,messages:args.messages,deadlineAt,maxTokens:args.maxTokens}})+'\n'));
  socket.on('error',()=>finish(Error('scanner_unavailable')));
  socket.on('end',()=>{if(!done)finish(Error('scanner_disconnected'));});
  socket.on('data',chunk=>{raw+=chunk;if(Buffer.byteLength(raw)>LIMITS.responseBytes+4096)return finish(Error('scanner_response_invalid'));if(!raw.includes('\n'))return;
   try{const result=JSON.parse(raw);if(result.error)throw Error();finish(null,result);}catch{finish(Error('scanner_response_invalid'));}
  });
 });
}
export function makeHermesSmart(config,directory){
 let selection;try{selection=resolveHermesScanner(config.scannerModel);if(selection.identity!==config.scannerIdentity)throw Error();}catch{return async()=>({verdict:'incomplete',findings:[],reason:'scanner_selection_unvalidated'});}
 return createSmart(selection,{complete:hermesCompletion(directory),resourceDir:capacityDirectory(path.dirname(config.inboxFile)),maxActive:config.maxActiveSmart,executionMode:'hermes-plugin-llm',allowFallback:true});
}
export async function hermesScan(host,selection,body){
 const entry=host.plugins.entries.antenna;
 return createSmart(selection,{complete:hermesCompletion(entry.settings?.socket_dir),resourceDir:capacityDirectory(path.dirname(entry.config.inboxFile)),executionMode:'hermes-plugin-llm',allowFallback:true})(body);
}
