# Hermes 1.7.0 candidate qualification — 2026-10-12

**Local implementation only. Not released, installed into a live profile, or ready
for catalog repinning.** Published 1.6.9 is unchanged. Reviewer clarification:
https://github.com/NousResearch/hermes-agent/pull/136652#issuecomment-6129125106
No reply was present at the latest check during this work.

## Implemented boundaries

- Receiver bearer read from a private, owned, non-symlink 0600 regular file;
  runtime and operator writes no longer persist it in YAML. Initialization can
  convert an explicitly supplied policy bearer; storage migration preserves it.
- Persistent profile data root matches the public `plugin_data_dir("antenna")`
  API. Code and data paths are separate across runtime, companion, pairing,
  local ClawReef state and recovery. Standalone CLI writers select the profile.
- Stopped migration validates first, copies and verifies, then selects new paths;
  old files remain. Interrupted copies can retry only if existing bytes match.
  Keys, receiver/peer tokens, policy, holds, replay and receipt history are retained.
- Backup uses the persistent root and exclusive profile lease. 1.6.8/1.6.9
  schema-2 archives convert inline bearer to file; they cannot supply receipts
  they never contained. Restore leaves Antenna disabled and retains unrelated
  host settings. The existing explicit age passphrase/restore confirmation remains.
- Shared profile leases cover plugin owners/standby, receiver and managed backend/
  bridge children, in-flight listeners and participating operator tools. Stable
  lock inode is outside restored files; no process-environment inspection.
- Foreign-host access rejected before reads; removed OpenClaw gateway admin and
  scanner credential paths. Cross-runtime wire protocol remains unchanged.
- Controlling-TTY `yes` required before held-message release. No PTY simulation
  instructed in bundled agent skills. Existing reason acknowledgments still apply.
- Collision-safe frames plus persisted original wire hashes for reconciliation.
- Removed forced canary installer; public process/privacy/upgrade disclosures.
- Version metadata is 1.7.0 candidate. Upstream standalone Hub additions from
  `959fc9c541f8e650549f548786ffa4bb0d346d26` incorporated and adapted for this
  unreleased version; no future download, tag or immutable pin is fabricated.

## Reproducible local checks

**Observed: 54 tests passed (51 Python, 3 Node).** The separate upstream approval
probe reproduced the open bypass paths; it is not counted as a safety pass.

Use an isolated Python environment with PyYAML, httpx==0.28.1 and
websockets==15.0.1, plus Node, jq, Bash/flock and OpenSSL. Tests use disposable
profiles/keys and fake host APIs, not live accounts or paid model providers.

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.mjs
```

The retained bridge/auth/supervisor regression tests now ship under `tests/` and
import this candidate's modules. They do not execute an unchanged old worktree.
Coverage includes profile exclusion, a killed receiver owner with a surviving
child, delayed in-flight host-call retirement, noninteractive/declined release,
private secret failure cases, migration interruption/conflict, old-archive
conversion, backup roundtrip, pairing/policy/companion consumers, signed live
HTTP admission, replay/peer/destination denial and held-message persistence.
The live socket/HTTP target and supervisor backend are fixture implementations,
not proof of a model turn on a full Hermes service.

Also checked: public plugin-storage API against a disposable profile; source
syntax; version metadata; local document links; skill frontmatter. Upstream
plugin static scanner is run against this candidate and its findings retained
in the local implementation record. The observed scanner verdict is **caution**,
with 31 findings, not a clean/safe result. Its single high-severity `proc_access`
match is the existing `lib/clawreef_http.py` owned signing-key descriptor passed
to OpenSSL, not another process’s environment. No scanner bypass was used.
A scanner result is not reviewer approval.

## Open gate: actual child execution approvals (H170-001)

The supervisor sanitizes inherited YOLO and session bypass markers and supplies
`HERMES_YOLO_MODE=0`. Parent values absent, enabled and false are tested; required
provider/startup settings remain. Per Corey's provisional choice, a YOLO parent
alone does not refuse startup. The reviewer has not accepted that choice yet.

**Sanitized environment alone is insufficient.** A disposable probe of the
reviewed upstream's real dotenv loader and `check_execute_code_guard` produced:

| Child configuration | Frozen YOLO | Approval decision |
| --- | --- | --- |
| Explicit unattended deny, manual mode | false | blocked |
| Same settings, profile `.env` enables YOLO | true | approved |
| `approvals.mode: off` | false | approved |

No code/command was executed by this probe. It only evaluated the approval path.
Reproduce with an upstream source path and extra test dependencies
`ruamel.yaml==0.18.17`, `python-dotenv==1.2.2`:

```sh
python tests/probe_upstream_approval.py /absolute/hermes-source
```

A final child-specific control must account for profile/project/managed dotenv,
configured approval bypass and session policy without silently changing the
operator's interactive policy or importing private runtime APIs in the plugin.
The actual `hermes serve` turn path must then be exercised; the probe's explicit
unattended context is not evidence of the server's context binding. This is a
release blocker, not a passing check. No new managed/admin overlay or runtime
patch has been introduced to make the test pass.

## Remaining integration gates (H170-010)

- Resolve and prove the child approval boundary; reconcile reviewer response.
- Native install/update/remove/reinstall on disposable full Hermes profiles,
  confirming retained identity and settings; directory separation tests are not
  a substitute for the native lifecycle test.
- Real live and headless signed delivery, holds/scanning and reload/takeover on
  disposable full runtime profiles; provider-backed Smart checks not run here.
- Encrypted age terminal interaction end to end. Archive validation, conversion,
  replacement and rollback mechanics are tested; encrypted CLI is not claimed.
- Qualify/update separately shipped 1.6.9 Diagnostics/Migration apps for
  `bearerFile`; do not assume their old bundled policy readers are compatible.
- Final catalog structural validation against the new immutable source pin,
  final-byte scanner review and package artifact checks. No final pin exists yet.

Only after those checks and separate publication authorization: immutable commit,
release assets, catalog repin and reviewer handoff. Never move v1.6.9's tag.
