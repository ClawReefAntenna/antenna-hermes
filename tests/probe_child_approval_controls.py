"""Characterize upstream child-policy controls, not a release safety test.

Uses the candidate launcher environment and real upstream loader, session store,
resume helper and approval guards. No model or requested command is executed.
Run with: python tests/probe_child_approval_controls.py /absolute/hermes-source
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hermes/headless'))
from managed import child_environment

UPSTREAM = Path(sys.argv[1]).resolve()
MANUAL = 'approvals: {mode: manual, unattended_mode: deny}\n'
CASES = [
    ('clean', {}, False),
    ('profile_dotenv_yolo', {'dotenv': 'HERMES_YOLO_MODE=1\n'}, True),
    ('project_dotenv_yolo_no_profile_env', {'project_env': 'HERMES_YOLO_MODE=1\n'}, True),
    ('managed_dotenv_yolo', {'managed_env': 'HERMES_YOLO_MODE=1\n'}, True),
    ('profile_approvals_off', {'config': 'approvals: {mode: "off"}\n'}, True),
    ('profile_unattended_approve', {'config': 'approvals: {mode: manual, unattended_mode: approve}\n'}, True),
    ('saved_session_yolo', {'session_yolo': True}, True),
    ('managed_manual_and_saved_yolo', {'managed_config': MANUAL, 'session_yolo': True}, True),
    ('managed_false_over_profile_yolo', {
        'dotenv': 'HERMES_YOLO_MODE=1\n', 'managed_env': 'HERMES_YOLO_MODE=0\n',
        'managed_config': MANUAL}, False),
    ('managed_false_and_saved_yolo', {
        'dotenv': 'HERMES_YOLO_MODE=1\n', 'managed_env': 'HERMES_YOLO_MODE=0\n',
        'managed_config': MANUAL, 'session_yolo': True}, True),
    ('approval_config_changed_after_import', {'reload_config': 'approvals: {mode: "off"}\n'}, True),
]

PROGRAM = r'''
import json, os
from pathlib import Path
from hermes_cli.env_loader import load_hermes_dotenv
case = json.loads(os.environ['PROBE_CASE'])
home = Path(os.environ['HERMES_HOME'])
load_hermes_dotenv(hermes_home=home, project_env=home.parent/'project.env', load_external_secrets=False)
from tools import approval
from tools.approval_context import set_current_session_key, reset_current_session_key
from tools.approval_yolo import restore_session_yolo
from hermes_state import SessionDB
from hermes_cli.subcommands.dashboard import build_serve_parser

# Same stored-value decoder and restore helper called by session.resume. This
# does not invoke the full RPC handler or pretend to be an actual serve turn.
db = SessionDB(db_path=home/'state.db')
db.create_session('probe-session', source='desktop', model_config={'yolo_mode': case.get('session_yolo', False)})
row = db.get_session('probe-session')
saved = SessionDB.session_yolo_enabled(row)
restored = restore_session_yolo('probe-session', saved)
token = set_current_session_key('probe-session')
if case.get('reload_config'):
    (home/'config.yaml').write_text(case['reload_config'])
try:
    result = {
        'frozen_yolo': approval._YOLO_MODE_FROZEN,
        'stored_yolo': saved,
        'restored_yolo': restored,
        'execute_code': approval.check_execute_code_guard('print("inert probe")', 'local'),
        'flagged_terminal': approval.check_all_command_guards('chmod 777 /tmp/antenna-inert-probe', 'local'),
        'ordinary_terminal': approval.check_all_command_guards('printf antenna-inert-probe', 'local'),
    }
    # A distinct profile has a distinct database, not the requested conversation.
    sibling = SessionDB(db_path=home.parent/'sibling-state.db')
    result['fresh_profile_has_target'] = sibling.get_session('probe-session') is not None
    sibling.close()
    parser = build_serve_parser(cmd_dashboard=lambda _: None)
    result['serve_options'] = sorted(parser._option_string_actions)
    print(json.dumps(result))
finally:
    reset_current_session_key(token)
    approval.clear_session('probe-session')
    db.close()
'''

results = {}
for name, case, expected_approved in CASES:
    with tempfile.TemporaryDirectory(prefix='ant-child-policy-') as directory:
        base = Path(directory)
        home = base/'profile'
        home.mkdir(mode=0o700)
        managed = base/'managed'
        managed.mkdir(mode=0o700)
        (home/'config.yaml').write_text(case.get('config', MANUAL))
        for key, path in [('dotenv', home/'.env'), ('project_env', base/'project.env'),
                          ('managed_env', managed/'.env'), ('managed_config', managed/'config.yaml')]:
            if key in case:
                path.write_text(case[key])
        # No real profile, credentials, external secret sources or system policy.
        parent = {k: os.environ[k] for k in ('PATH', 'LANG', 'SYSTEMROOT') if k in os.environ}
        parent.update(HOME=directory, XDG_CONFIG_HOME=str(base/'config'),
                      XDG_DATA_HOME=str(base/'data'), HERMES_YOLO_MODE='1')
        env = child_environment(parent, {'home': str(home)}, 'fixture-token', 'fixture-password')
        assert parent['HERMES_YOLO_MODE'] == '1' and env['HERMES_YOLO_MODE'] == '0'
        env.update(HERMES_MANAGED_DIR=str(managed), HERMES_SESSION_PLATFORM='api_server',
                   PYTHONPATH=str(UPSTREAM), PROBE_CASE=json.dumps(case))
        process = subprocess.run([sys.executable, '-c', PROGRAM], cwd=directory, env=env,
                                 capture_output=True, text=True, timeout=30)
        if process.returncode:
            raise RuntimeError(f'{name}: {process.stderr}')
        result = json.loads(process.stdout.strip().splitlines()[-1])
        for gate in ('execute_code', 'flagged_terminal'):
            assert result[gate]['approved'] is expected_approved, (name, gate, result)
        assert result['ordinary_terminal']['approved'] is True, (name, result)
        assert result['fresh_profile_has_target'] is False
        results[name] = result

print(json.dumps({'scope': 'decision paths only; no serve turn or action execution',
                  'cases': results}, indent=2))
