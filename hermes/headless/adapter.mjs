// No child launch or backend attachment until Hermes supplies a verified control.
// Live-session delivery uses ../adapter.mjs and its normal host approval policy.
export function makeHeadlessAdapter() {
 return {
  resolve:async()=>false,
  submit:async()=>({status:'unavailable',reason:'headless_approval_control_unavailable'})
 };
}
