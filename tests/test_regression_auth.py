# Retained Antenna headless regression harness, now targeting this candidate.
import sys
from pathlib import Path
HEADLESS=Path(__file__).resolve().parents[1]/'hermes/headless'
sys.path.insert(0,str(HEADLESS))
import asyncio,json,os,tempfile,unittest
from pathlib import Path
import httpx
from auth import authenticate,websocket_query
class Auth(unittest.IsolatedAsyncioTestCase):
 async def test_loopback_bearer_unchanged(self):
  async with httpx.AsyncClient(base_url='http://127.0.0.1',transport=httpx.MockTransport(lambda q:httpx.Response(200))) as h:
   self.assertFalse(await authenticate(h,{}));self.assertEqual(await websocket_query(h,'x',False),'token=x')
 async def test_gated_cookie_cache_and_ticket(self):
  with tempfile.TemporaryDirectory() as root:
   p=Path(root)/'login';p.write_text(json.dumps({'username':'test','password':'private'}));p.chmod(0o600);c={'login_file':str(p),'cookie_file':str(Path(root)/'cookies')};counts={'login':0}
   def server(q):
    if q.url.path=='/auth/password-login':
     self.assertNotIn('authorization',q.headers);counts['login']+=1;return httpx.Response(200,headers={'set-cookie':'session=valid; Path=/'})
    if q.headers.get('authorization'):return httpx.Response(401)
    if q.headers.get('cookie')!='session=valid':return httpx.Response(401)
    return httpx.Response(200,json={'ticket':'one-use'})
   for _ in range(2):
    async with httpx.AsyncClient(base_url='http://127.0.0.1',headers={'Authorization':'Bearer old'},transport=httpx.MockTransport(server)) as h:
     self.assertTrue(await authenticate(h,c));self.assertEqual(await websocket_query(h,'old',True),'ticket=one-use')
   self.assertEqual(counts['login'],1);self.assertEqual(Path(c['cookie_file']).stat().st_mode&0o777,0o600)
 async def test_missing_credentials_refused(self):
  async with httpx.AsyncClient(base_url='http://127.0.0.1',transport=httpx.MockTransport(lambda q:httpx.Response(401))) as h:
   with self.assertRaises(httpx.HTTPStatusError):await authenticate(h,{})
 async def test_non_auth_error_not_reinterpreted(self):
  async with httpx.AsyncClient(base_url='http://127.0.0.1',transport=httpx.MockTransport(lambda q:httpx.Response(503))) as h:
   with self.assertRaises(httpx.HTTPStatusError):await authenticate(h,{})
if __name__=='__main__':unittest.main()
