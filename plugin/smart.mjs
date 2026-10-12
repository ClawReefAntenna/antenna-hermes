import {LIMITS} from './limits.mjs';
import {acquire} from './capacity.mjs';
import {rubric,RUBRIC,validateVerdict} from './scanners.mjs';
const incomplete=reason=>({schema:1,version:RUBRIC,verdict:'incomplete',findings:[],reason});
export function createSmart(selection,{complete,resourceDir,maxActive=LIMITS.active,deadlineMs=LIMITS.smartMs,executionMode='isolated-agent-runtime',allowFallback=false}={}){
 if(!Number.isInteger(deadlineMs)||deadlineMs<1||deadlineMs>LIMITS.smartMs||!Number.isInteger(maxActive)||maxActive<1||maxActive>LIMITS.active)throw Error('invalid scanner bounds');
 let active=0;
 return async(body,{deadlineAt=Date.now()+deadlineMs}={})=>{
  if(typeof complete!=='function')return incomplete('runtime_scanner_unavailable');
  if(typeof body!=='string'||Buffer.byteLength(body)>LIMITS.bodyBytes)return incomplete('input_size');
  const prompt=JSON.stringify({untrusted_message:body});
  if(Buffer.byteLength(prompt)+Buffer.byteLength(rubric)>LIMITS.requestBytes)return incomplete('request_budget');
  if(active>=maxActive)return incomplete('scanner_capacity');
  active++;let release,timer,requests=0;const controller=new AbortController(),began=performance.now();
  try{
   const deadline=Math.min(deadlineAt,Date.now()+deadlineMs);
   release=await acquire('smart',deadline,resourceDir);if(!release)return incomplete('scanner_capacity');
   const remaining=deadline-Date.now();if(remaining<=0)return incomplete('scheduling_deadline');
   const timeout=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(Error('scanner_timeout'));},remaining);});
   requests=1;
   const result=await Promise.race([complete({model:selection.modelId,systemPrompt:rubric,messages:[{role:'user',content:prompt}],purpose:'antenna.mcs',maxTokens:LIMITS.outputTokens,signal:controller.signal,execution:{mode:executionMode,timeoutMs:remaining}}),timeout]);
   if(result.execution?.mode!==executionMode||result.stopReason&&result.stopReason!=='stop'||typeof result.text!=='string'||Buffer.byteLength(result.text)>LIMITS.responseBytes) return {...incomplete('invalid_runtime_response'),requests};
   if(!allowFallback&&result.provider+'/'+result.model!==selection.modelId)return {...incomplete('model_identity_changed'),requests};
   const value=validateVerdict(JSON.parse(result.text),body);
   return {...value,version:RUBRIC,model:selection.modelId,...(allowFallback?{returnedModel:[result.provider??'unknown',result.model??'unknown'].join('/').slice(0,128),requestAccounting:'host calls; internal retries/fallback not counted'}:{}),requests,elapsedMs:performance.now()-began};
  }catch(e){
   // Stable runtime codes only; never return raw provider errors or credentials.
   const reason=typeof e.code==='string'&&/^[A-Z0-9_]{1,80}$/.test(e.code)?e.code:'runtime_scanner_failed';
   return {...incomplete(reason),requests,elapsedMs:performance.now()-began};
  }finally{clearTimeout(timer);controller.abort();if(release)await release();active--;}
 };
}
