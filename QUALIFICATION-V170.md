# Hermes 1.7.0 candidate qualification — 2026-10-12

**Local implementation only. Not released, installed into a live profile, or ready
for catalog repinning.** Published 1.6.9 is unchanged. Reviewer clarification:
https://github.com/NousResearch/hermes-agent/pull/136652#issuecomment-6129125106
No reply was present at the latest check during this work.

## Headless-only availability decision — follow-through

Corey accepted the headless-only scope and the supported Hermes-owned control,
not an Antenna settings/session monitoring workaround. Until that control exists
and is verified, this candidate disables headless delivery. Interactive YOLO and
live-session approval policy are unchanged. This is not upstream implementation
or reviewer acceptance; the headless re-enablement and overall release gates stay open.

- Saved `headless.enabled: true` logs a limitation but starts only the normal live
  receiver. No settings are rewritten, and exact live-session routing is retained.
- Supervisor launch, bridge CLI/library submission and Node headless adapter
  refuse before launching a backend or submitting a prompt. There is no override.
- Owner-local release ignores stale backend pointers and uses the same live-session
  adapter as ingress; closed/unregistered targets stay unavailable.
- No profile/YOLO inspection loop, alternate profile or private Hermes patch added.

Current checks: **55 tests passed: 50 Python + 5 Node**. Four supervisor-refusal/live
service tests replace the five historical supervisor/validation tests; two Node
refusal/pointer tests were added. No tests were skipped. Fixture profiles with YOLO
and approval mode off, dotenv and session-history bytes stayed unchanged. The real
Node receiver starts with stale/incomplete headless settings; signed HTTP ingress
still reaches the exact live socket. Direct supervisor/bridge/adapter tests refuse.
The live Hermes injection endpoint is a fixture, not a real model turn.

Three retained receipt tests explicitly mock admission with fully fake HTTP/WS
transports; these only protect receipt behavior for future integration. Historical
supervisor shutdown tests are no longer current headless execution qualification.
No actual restricted `hermes serve` turn was run: headless cannot start.

Both bundled agent skills validate; whitespace checks pass. The broad Node glob
also ran the argument-requiring standalone optional-app probe and failed for missing
paths. The corrected explicit test command below passes all five Node tests; the
probe is separate characterization and not included in that count.

## Integration follow-through — optional apps, recovery and native lifecycle

- Matching local optional-app candidates are built from clean commits: Diagnostics
  `98f5c34`, Migration `c3c6027`. Shared runtime helpers are pinned to core `6f7d008`.
  Extracted archives pass 41 reported checks (20 Diagnostics, 21 Migration), with
  84 offline corpus cases and fixture-only Smart calls. File-backed credentials
  work; unsafe files/conflicts fail; Migration exports/applies the reference, not
  the resolved token. Published 1.6.9 apps remain incompatible.
- Actual `age` encryption/decryption through a controlling terminal passed six
  disposable checks: create plus reopen, verify, wrong passphrase, preview,
  declined restore and confirmed restore. Generated identity keys, replay and
  receipt history round-trip; bearer stays outside YAML, plugin stays disabled,
  and unrelated host settings remain. No live profile or user key was used.
- Native CLI on reviewed runtime source `00e5cf64a829232a6daceb3a8ad327106e56fe08`
  installs disabled, removes and reinstalls the candidate while retaining external
  fixture identity/bearer/inbox/replay/receipt bytes. Removal deletes registration
  as documented; reinstall alone does not restore those settings. Unrelated
  settings and interactive YOLO survive.
- **Native update is not qualified:** the CLI rejects the candidate with its
  caution verdict and asks for `--force`. No forced update, scan disable or
  kill-list override was used. Installation used the native interactive caution
  confirmation after review. The failed update left state/settings unchanged.

These are local results, not catalog approval or release authorization. Full
live-runtime/Smart/reload tests and final-byte scan outcomes must still be reported
separately. All headless paths remain disabled.

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

**Historical initial checkpoint: 54 tests passed (51 Python, 3 Node).** Current
follow-through counts are above. The separate upstream approval
probe reproduced the open bypass paths; it is not counted as a safety pass.

Use an isolated Python environment with PyYAML, httpx==0.28.1 and
websockets==15.0.1, plus Node, jq, Bash/flock and OpenSSL. Tests use disposable
profiles/keys and fake host APIs, not live accounts or paid model providers.

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/delivery.mjs tests/framing.mjs tests/headless-unavailable.mjs
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

The findings below explain why headless is now disabled. They describe the earlier
launch implementation, not an enabled path in this candidate.

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

### Follow-up investigation

The [child-control investigation](CHILD-APPROVAL-INVESTIGATION.md) adds 11
disposable decision-path scenarios using the real candidate environment builder,
upstream SQLite session state, resume helper and code/terminal guards. Saved
session YOLO bypasses even a temporary manual/YOLO-false managed configuration;
post-import approval config changes also affect decisions. No tested action or
actual server turn was executed. These are reproduced bypasses, not safety passes.
No supported approval-floor launch option was found in the reviewed upstream.
Recommended next implementation is a Hermes-owned child restriction; a new
profile is not a transparent substitute for resuming existing conversations.

The same investigation confirmed both existing optional-app policy readers reject
a `bearerFile`-only policy that the candidate accepts. Compatibility is now a
reproduced gap, still not fixed. Production code and interactive settings remain
unchanged by this investigation; all release gates below remain open.

## Remaining integration gates (H170-010)

- Keep headless disabled until the supported host control and actual-server proof
  satisfy the contract; reconcile reviewer response. The gate is not an upstream fix.
- Complete native update qualification after resolving the native caution/force
  gate. Install/remove/reinstall retention passed on a disposable full profile;
  plugin registration is deliberately removed and must be restored separately.
- Real live and headless signed delivery, holds/scanning and reload/takeover on
  disposable full runtime profiles; provider-backed Smart checks not run here.
- Encrypted age terminal interaction: six end-to-end disposable checks passed.
  Retain this result in the final artifact handoff; no live restore was performed.
- Matching 1.7.0 Diagnostics/Migration candidates pass extracted-package tests;
  final scan/publication gates remain. Published 1.6.9 readers are not compatible.
- Final catalog structural validation against the new immutable source pin,
  final-byte scanner review and package artifact checks. No final pin exists yet.

Only after those checks and separate publication authorization: immutable commit,
release assets, catalog repin and reviewer handoff. Never move v1.6.9's tag.
