"""Opt-in headless delivery candidate. Public Hermes HTTP/WS only; no runtime imports.

Input is local, already authorized/scanned by ReceiveFlow. Additional exact grants
are required here. Unknown outcomes never trigger automatic resubmission.
"""
import asyncio,hashlib,ipaddress,json,os,re,sqlite3,stat,sys,uuid
from pathlib import Path
from contextlib import contextmanager
from urllib.parse import urlsplit,quote
from auth import authenticate,websocket_query
from message_frame import frame_peer_message
import httpx
from websockets.asyncio.client import connect

class Refused(Exception): pass

def private(path,directory=False):
    p=Path(path);s=p.lstat()
    if s.st_uid!=os.getuid() or s.st_mode&0o077 or stat.S_ISLNK(s.st_mode):raise Refused()
    if not (stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode)):raise Refused()
    return p

def digest(value):return hashlib.sha256(value.encode()).hexdigest()

class Bridge:
    def __init__(self,config):
        self.c=json.loads(private(config).read_text())
        u=urlsplit(self.c['origin'])
        if u.scheme!='http' or not ipaddress.ip_address(u.hostname).is_loopback or not u.port or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:raise Refused()
        self.origin=self.c['origin'].rstrip('/')
        self.token=private(self.c['token_file']).read_text().strip()
        if not self.token:raise Refused()
        state=private(self.c['state_dir'],True);self.db=state/'receipts.sqlite'
        if self.db.exists():private(self.db)
        with self.store() as db:db.execute('create table if not exists receipts(peer text, mid text, digest text, target text, wirehash text, result text, primary key(peer,mid))')
        os.chmod(self.db,0o600)
    @contextmanager
    def store(self):
        db=sqlite3.connect(self.db,timeout=10);db.execute('pragma synchronous=FULL')
        try:
            with db:yield db
        finally:db.close()
    def target(self,key):
        if not isinstance(key,str) or not re.fullmatch(r'agent:'+re.escape(self.c.get('agent_id','main'))+r':[A-Za-z0-9_-]{1,100}',key):raise Refused()
        if not any(key in v for v in self.c['grants'].values()):raise Refused()
        return key.split(':',2)[2]
    async def detail(self,http,key):
        r=await http.get('/api/sessions/'+quote(key,safe=''));r.raise_for_status();d=r.json()
        if d.get('id')!=key or d.get('profile')!='default':raise Refused()
        return d
    async def lineage(self,http,key):
        root=await self.detail(http,key)
        r=await http.get('/api/sessions/'+quote(key,safe='')+'/latest-descendant');r.raise_for_status();route=r.json()
        chain=route.get('path')
        if not isinstance(chain,list) or not 1<=len(chain)<=32 or chain[0]!=key or chain[-1]!=route.get('session_id') or len(set(chain))!=len(chain):raise Refused()
        parent=root
        for childid in chain[1:]:
            child=await self.detail(http,childid)
            cfg=child.get('model_config') or {}
            if isinstance(cfg,str):cfg=json.loads(cfg)
            if parent.get('end_reason')!='compression' or child.get('parent_session_id')!=parent['id'] or child.get('source')=='tool' or any(cfg.get(k) is not None for k in ['_branched_from','_delegate_from','_reset_from']):raise Refused()
            parent=child
        return chain[-1]
    async def rpc(self,ws,method,**params):
        rid=str(uuid.uuid4());await ws.send(json.dumps({'jsonrpc':'2.0','id':rid,'method':method,'params':params}))
        async with asyncio.timeout(25):
            while True:
                for line in (await ws.recv()).splitlines():
                    msg=json.loads(line)
                    if msg.get('id')==rid:return msg
    def save(self,peer,mid,result):
        with self.store() as db:db.execute('update receipts set result=? where peer=? and mid=?',(json.dumps(result),peer,mid))
        return result
    @staticmethod
    def queued(m):
        meta=m.get('display_metadata') or {}
        if isinstance(meta,str):meta=json.loads(meta)
        return bool(meta.get('_queued_prompt'))
    async def reconcile(self,http,target,wirehash):
        # Bounded read-only search. No match means unknown, never permission to replay.
        r=await http.get('/api/sessions/'+quote(target,safe='')+'/messages',params={'limit':500,'order':'latest','inline_images':'false'});r.raise_for_status()
        data=r.json();messages=data.get('messages',[]) if isinstance(data,dict) else data
        matches=[m for m in messages if m.get('role')=='user' and isinstance(m.get('content'),str) and digest(m['content'])==wirehash and m.get('active',1) and not self.queued(m)]
        return {'status':'submitted','reason':'runtime_persisted','row_id':matches[0].get('id'),'reconciled':True} if len(matches)==1 else None
    async def run(self,q):
        os.umask(0o077)
        target=self.target(q.get('target'))
        async with httpx.AsyncClient(base_url=self.origin,headers={'Authorization':'Bearer '+self.token},trust_env=False,follow_redirects=False,timeout=10) as http:
            gated=await authenticate(http,self.c)
            resolved=await self.lineage(http,target)
            if q.get('op')=='resolve':return {'available':True}
            if q.get('op')!='submit':raise Refused()
            f=q.get('fields',{});peer=f.get('from');mid=f.get('message_id');body=f.get('body')
            if not isinstance(peer,str) or q['target'] not in self.c['grants'].get(peer,[]) or not isinstance(mid,str) or not re.fullmatch(r'[0-9a-f-]{36}',mid) or not isinstance(body,str) or len(body)>10000:raise Refused()
            payload=json.dumps([q['target'],body],ensure_ascii=False);hashed=digest(payload)
            wire=frame_peer_message(peer,body)+f'\nAntenna receipt: {mid}'
            wh=digest(wire)
            with self.store() as db:
                db.execute('begin immediate')
                old=db.execute('select digest,result,wirehash from receipts where peer=? and mid=?',(peer,mid)).fetchone()
                if old:
                    if old[0]!=hashed:return {'status':'rejected','reason':'message_id_conflict'}
                else:db.execute('insert into receipts values(?,?,?,?,?,?)',(peer,mid,hashed,target,wh,json.dumps({'status':'unknown','reason':'confirmation_unavailable'})))
            if old:
                result=json.loads(old[1])
                if result['status']=='unknown':
                    # A fresh nonce must not change the identity of the already
                    # submitted wire. This also supports legacy fixed-frame rows.
                    try:found=await self.reconcile(http,resolved,old[2])
                    except Exception:found=None
                    if found:return self.save(peer,mid,found)
                return result
            try:
                query=await websocket_query(http,self.token,gated)
                async with connect(self.origin.replace('http:','ws:',1)+'/api/ws?'+query,open_timeout=10,max_size=8_000_000) as ws:
                    r=await self.rpc(ws,'session.resume',session_id=target,source='desktop',omit_messages=True)
                    if 'error' in r:return self.save(peer,mid,{'status':'unavailable','reason':'resume_refused'})
                    active=r.get('result',{})
                    if active.get('session_key')!=resolved or await self.lineage(http,target)!=resolved:return self.save(peer,mid,{'status':'unavailable','reason':'lineage_changed'})
                    r=await self.rpc(ws,'prompt.submit',session_id=active['session_id'],queued=True,text=wire)
                    if 'error' in r:return self.save(peer,mid,{'status':'unavailable','reason':'runtime_refused','code':r['error'].get('code')})
                    row=r.get('result',{}).get('user_row_id')
                    if isinstance(row,int) and not isinstance(row,bool):return self.save(peer,mid,{'status':'submitted','reason':'runtime_persisted','row_id':row})
                    # Queue response has no final row receipt. Do not call it persisted.
                    return {'status':'unknown','reason':'confirmation_unavailable'}
            except Exception:return {'status':'unknown','reason':'confirmation_unavailable'}

async def main():
    os.umask(0o077)
    q={}
    try:
        raw=sys.stdin.read(50000)
        if len(raw)>=50000:raise Refused()
        q=json.loads(raw);result=await Bridge(sys.argv[1]).run(q)
    except Exception:
        result=({'status':'unknown','reason':'confirmation_unavailable'} if isinstance(q,dict) and q.get('op')=='submit' else {'available':False,'status':'unavailable','reason':'headless_unavailable'})
    print(json.dumps(result))
if __name__=='__main__':asyncio.run(main())
