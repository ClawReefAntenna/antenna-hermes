"""Fresh registration is inert; partial configuration must not enter that state."""
import sys,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hermes
class Context:
    def __init__(self,config): self.config=config;self.hooks={}
    def get_config(self,key,default=None):return self.config.get(key,default)
    def register_skill(self,*args):pass
    def register_hook(self,name,fn):self.hooks[name]=fn
class Registration(unittest.TestCase):
    def test_blank_registration_never_starts_or_opens_storage(self):
        ctx=Context({})
        with patch.object(hermes,'private_data_directory',side_effect=AssertionError('storage accessed')),patch.object(hermes,'ProfileLease',side_effect=AssertionError('lease acquired')),patch.object(hermes,'ReceiverService',side_effect=AssertionError('receiver started')),patch.object(hermes,'Listener',side_effect=AssertionError('listener started')):
            with self.assertLogs('hermes',level='WARNING') as logs:hermes.register(ctx)
            self.assertEqual(len(ctx.hooks),4)
            for fn in ctx.hooks.values():self.assertIsNone(fn(session_id='existing',platform='tui'))
            self.assertIn('unconfigured and inactive',logs.output[0])
    def test_every_recognized_explicit_key_avoids_inactive_path(self):
        storage=types.ModuleType('plugins.plugin_storage')
        def denied(*args):raise ValueError('normal storage path reached')
        storage.plugin_data_dir=denied
        for key in (*hermes.POLICY_KEYS,'bearer','socket_dir','listen_port','agent_id','headless'):
            ctx=Context({key:None})
            with self.subTest(key=key),patch.dict(sys.modules,{'plugins':types.ModuleType('plugins'),'plugins.plugin_storage':storage}):
                with self.assertRaises((ValueError,TypeError)):hermes.register(ctx)
                self.assertEqual(ctx.hooks,{})
    def test_partial_config_is_rejected_by_existing_port_guard(self):
        with self.assertRaisesRegex(ValueError,'private socket_dir'):hermes.register(Context({'listen_port':18792}))
if __name__=='__main__':unittest.main()
