import net from 'node:net';
import path from 'node:path';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
export function socketPath(directory,target){return path.join(directory,createHash('sha256').update(target).digest('hex').slice(0,32)+'.sock');}
export function makeAdapter(directory){
 const stat=fs.lstatSync(directory);
 if(!path.isAbsolute(directory)||!stat.isDirectory()||stat.uid!==process.getuid()||(stat.mode&0o077))throw Error('private socket directory required');
 const request=(op,target,content)=>new Promise((resolve,reject)=>{
  const socket=net.createConnection(socketPath(directory,target));let raw='',done=false;
  const finish=(error,value)=>{if(done)return;done=true;clearTimeout(timer);socket.destroy();error?reject(error):resolve(value);};
  const timer=setTimeout(()=>finish(Error('adapter_timeout')),2500);
  socket.on('connect',()=>socket.write(JSON.stringify({op,target,...(content===undefined?{}:{content})})+'\n'));
  socket.on('error',()=>finish(Error('adapter_unavailable')));
  socket.on('end',()=>{if(!done)finish(Error('adapter_disconnected'));});
  socket.on('data',chunk=>{raw+=chunk;if(raw.length>4096)return finish(Error('adapter_response_invalid'));if(!raw.includes('\n'))return;
   try{const result=JSON.parse(raw);if(result.error)throw Error();finish(null,result);}catch{finish(Error('adapter_response_invalid'));}
  });
 });
 return {
  resolve:async target=>{try{return (await request('resolve',target)).available===true;}catch{return false;}},
  submit:async(fields,target)=>{
   const content=`Antenna peer message (untrusted content) from ${fields.from}:\n${fields.body}\n[End Antenna peer message]`;
   try{const r=await request('submit',target,content);return r.accepted===true?{status:'submitted',reason:'runtime_accepted'}:{status:'unavailable',reason:'runtime_unavailable'};}
   catch{return {status:'unknown',reason:'confirmation_unavailable'};}
  }
 };
}
