"""Read-only upstream decision-path probe; no commands execute, no live profile.

Usage: python tests/probe_upstream_approval.py /absolute/hermes-source
This is an integration qualification probe, not a substitute for real serve turns.
"""
import json,os,subprocess,sys,tempfile
from pathlib import Path
upstream=Path(sys.argv[1]).resolve()
program='''
import json,os
from hermes_cli.env_loader import load_hermes_dotenv
load_hermes_dotenv(hermes_home=os.environ['HERMES_HOME'],load_external_secrets=False)
from tools.approval import _YOLO_MODE_FROZEN,check_execute_code_guard
print(json.dumps({'frozen_yolo':_YOLO_MODE_FROZEN,'decision':check_execute_code_guard('print("inert example")','local')}))
'''
results={}
for name,envfile,config in [('normal','', 'approvals: {mode: manual, unattended_mode: deny}'),
                             ('profile_dotenv_yolo','HERMES_YOLO_MODE=1\n','approvals: {mode: manual, unattended_mode: deny}'),
                             ('profile_approvals_off','','approvals: {mode: "off"}')]:
 with tempfile.TemporaryDirectory(prefix='ant-approval-probe-') as directory:
  home=Path(directory);(home/'.env').write_text(envfile);(home/'config.yaml').write_text(config)
  env={k:v for k,v in os.environ.items() if not k.startswith('HERMES_')}
  env.update(HERMES_HOME=directory,HERMES_YOLO_MODE='0',HERMES_SESSION_PLATFORM='api_server',PYTHONPATH=str(upstream))
  p=subprocess.run([sys.executable,'-c',program],cwd=directory,env=env,capture_output=True,text=True,timeout=30)
  if p.returncode:print(p.stderr,file=sys.stderr);sys.exit(1)
  results[name]=json.loads(p.stdout.strip().splitlines()[-1])
print(json.dumps(results,indent=2))
assert not results['normal']['frozen_yolo']
assert results['profile_dotenv_yolo']['frozen_yolo']
