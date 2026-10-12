import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {makeHeadlessAdapter} from '../hermes/headless/adapter.mjs';
import {managedOptions} from '../hermes/receiver.mjs';

test('direct headless adapter cannot launch even with an executable/config supplied',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'ant-disabled-'));
 try{
  const marker=path.join(root,'executed'),launcher=path.join(root,'python');
  fs.writeFileSync(launcher,`#!/bin/sh\ntouch '${marker}'\n`,{mode:0o700});
  const adapter=makeHeadlessAdapter({python:launcher,config:path.join(root,'config')});
  assert.equal(await adapter.resolve('agent:main:saved'),false);
  assert.deepEqual(await adapter.submit({},'agent:main:saved'),{status:'unavailable',reason:'headless_approval_control_unavailable'});
  assert.equal(fs.existsSync(marker),false);
 }finally{fs.rmSync(root,{recursive:true});}
});

test('held-message delivery ignores stale headless pointer and selects live mode',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'ant-pointer-'));
 try{
  const pointer=path.join(root,'headless-active.json');
  fs.writeFileSync(pointer,'not even valid JSON',{mode:0o600});
  for(const settings of [{enabled:true,python:'/old/python'},{enabled:false},{}])
   assert.deepEqual(managedOptions(root,settings),{});
  assert.equal(fs.readFileSync(pointer,'utf8'),'not even valid JSON');
 }finally{fs.rmSync(root,{recursive:true});}
});
