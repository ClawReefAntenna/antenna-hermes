import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {makeHeadlessAdapter} from '../hermes/headless/adapter.mjs';
import {managedOptions} from '../hermes/receiver.mjs';

test('headless adapter preserves bridge policy refusal',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'ant-policy-'));
 try{
  const launcher=path.join(root,'python');
  fs.writeFileSync(launcher,`#!/bin/sh\ncat >/dev/null\nprintf '%s\\n' '{"available":false,"status":"unavailable","reason":"headless_yolo_target"}'\n`,{mode:0o700});
  const adapter=makeHeadlessAdapter({python:launcher,config:path.join(root,'config')});
  assert.equal(await adapter.resolve('agent:main:saved'),false);
  assert.deepEqual(await adapter.submit({},'agent:main:saved'),{available:false,status:'unavailable',reason:'headless_yolo_target'});
 }finally{fs.rmSync(root,{recursive:true});}
});

test('held-message delivery requires matching private managed pointer',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'ant-pointer-'));
 try{
  const pointer=path.join(root,'headless-active.json');
  assert.deepEqual(managedOptions(root,{enabled:false}),{});
  assert.throws(()=>managedOptions(root,{enabled:true,python:'/python'}));
  fs.writeFileSync(pointer,JSON.stringify({python:'/python',config:path.join(root,'bridge.json')}),{mode:0o600});
  assert.deepEqual(managedOptions(root,{enabled:true,python:'/python'}),{headless:{python:'/python',config:path.join(root,'bridge.json')}});
  assert.throws(()=>managedOptions(root,{enabled:true,python:'/other'}));
  fs.chmodSync(pointer,0o644);
  assert.throws(()=>managedOptions(root,{enabled:true,python:'/python'}));
 }finally{fs.rmSync(root,{recursive:true});}
});
