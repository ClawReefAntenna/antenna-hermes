// Opt-in candidate. Invoked after the existing ReceiveFlow authorization/scans.
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs';
const script=fileURLToPath(new URL('./bridge.py',import.meta.url));
export function makeHeadlessAdapter({python,config}) {
 if(!python?.startsWith('/')||!config?.startsWith('/'))throw Error('absolute headless paths required');
 const request=q=>new Promise((resolve,reject)=>{
  const fd=process.env.ANTENNA_PROFILE_LEASE_FD===undefined?null:Number(process.env.ANTENNA_PROFILE_LEASE_FD);
  if(fd!==null&&(!Number.isInteger(fd)||fd<3))return reject(Error('invalid profile lease'));
  if(fd!==null)fs.fstatSync(fd);
  const child=spawn(python,[script,config],{stdio:fd===null?['pipe','pipe','ignore']:['pipe','pipe','ignore',fd],env:fd===null?process.env:{...process.env,ANTENNA_PROFILE_LEASE_FD:'3'}});let output='';
  const timer=setTimeout(()=>{child.kill('SIGTERM');reject(Error('headless_timeout'));},55000);
  child.on('error',()=>{clearTimeout(timer);reject(Error('headless_unavailable'));});
  child.stdout.on('data',chunk=>{output+=chunk;if(output.length>8192){child.kill('SIGTERM');}});
  child.on('close',code=>{clearTimeout(timer);try{if(code!==0||output.length>8192)throw Error();resolve(JSON.parse(output));}catch{reject(Error('headless_unavailable'));}});
  child.stdin.on('error',()=>{});child.stdin.end(JSON.stringify(q));
 });
 return {
  resolve:async target=>{try{return (await request({op:'resolve',target})).available===true;}catch{return false;}},
  submit:async(fields,target)=>{try{return await request({op:'submit',target,fields:{from:fields.from,message_id:fields.message_id,body:fields.body}});}catch{return {status:'unknown',reason:'confirmation_unavailable'};}}
 };
}
