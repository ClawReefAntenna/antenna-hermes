# Child-only approval control — bounded investigation

> **Superseded headless posture — 2026-10-13:** The historical blanket-disable and
> proposed upstream-control requirements below are not the current scope. The
> candidate now integrates a delivery-time public-API check: non-YOLO targets may
> receive headless messages; saved/effective YOLO or unverifiable targets are
> refused. No Hermes changes or continuous monitoring. See
> [current behavior](hermes/headless/README.md). Historical results below remain
> evidence for their recorded revisions, not current headless qualification.


2026-10-12. **Investigation complete; H170-001 remains blocked.** No live profile,
interactive setting, production launcher, upstream runtime or public release was
changed. This is not a claim that the candidate is safe to deploy.

## Owner decision and local follow-through

After this investigation, Corey accepted the supported Hermes-owned restriction
with headless-only scope, leaving interactive YOLO and live-session approvals
unchanged. He authorized proceeding with the recommendation to keep headless
unavailable until that control exists and is verified. The variation involving
continuous Antenna checks of settings and saved sessions was rejected as needless
complexity.

The candidate now enforces that unavailable posture at supervisor and bridge
entry points and retains live-session delivery even when old headless settings
remain. This is **not** a Hermes control implementation, a capability detector,
an upstream submission, or approval to publish. No current Hermes version is
asserted to support the proposed contract. See [current verification](QUALIFICATION-V170.md).

## Finding and recommendation

The reviewed Hermes source has no supported `serve` launch option imposing an
approval restriction that survives all of dotenv loading, live profile settings
and saved-session YOLO restoration. Recommend a **Hermes-owned, process-local
approval floor for unattended children**, exposed through its supported launch
interface. Do not implement this by importing or patching private runtime APIs
from Antenna, or by rewriting the operator's interactive profile.

This finding is scoped to reviewed Hermes commit
`97a9ae8ee55d31bebce49f1fb6b5ef775323976a`, in the clean catalog checkout
`00e5cf64a829232a6daceb3a8ad327106e56fe08` (catalog-only addition). Latest remote
main and a new reviewer response were not checked in this investigation.

### Supported surfaces inspected

- `hermes_cli/subcommands/dashboard.py`: `serve --isolated` controls profile/server
  routing, not approvals. The real parser exposes no approval-floor option.
- `hermes_cli/env_loader.py::load_hermes_dotenv`: profile dotenv overrides shell
  values; project dotenv overrides them when the profile file is absent; managed
  dotenv applies last. Setting `HERMES_YOLO_MODE=0` at launch is not authoritative.
- `tools/approval.py`: process YOLO, session YOLO and `approvals.mode: off` bypass
  normal gates. Approval configuration is read during guard checks, not just boot.
- `tui_gateway/methods_session.py::_handle_session_resume`: restores stored YOLO
  using `SessionDB.session_yolo_enabled` and `restore_session_yolo`. Antenna's
  bridge uses `session.resume`, followed by `prompt.submit`, for existing targets.
- `tui_gateway/server.py::_enable_gateway_prompts`: the server installs gateway,
  ask and interactive markers. An `api_server` decision probe is **not** proof of
  the desktop/WebSocket turn's actual context or approval lifecycle.
- `hermes_cli/managed_scope.py`: administrator overlay is not a child-policy API;
  its config parse failure is fail-open. Even a valid overlay forcing manual mode
  and YOLO false does not override saved-session YOLO. No managed overlay was
  installed in Antenna; probe overlays existed only in temporary fixture trees.
- Public observer-hook documentation: approval hooks are observer-only;
  `pre_tool_call` can block tools, but callback failures are fail-open. Building
  an independent command policy here is not the requested host approval floor.

## Reproduced decision paths

`tests/probe_child_approval_controls.py` uses the **candidate's actual environment
builder** with a YOLO parent, the real upstream loader, a disposable SQLite
session round-trip, the same restoration helper used by resume, and both real
approval guards. It does not mock approval decisions or execute the tested code
or shell strings. No model/provider request is made.

All 11 scenarios matched their stated expectations. This is successful
**characterization of bypasses**, not 11 successful security checks.

| Child condition | Code and flagged terminal decisions | Ordinary terminal decision |
| --- | --- | --- |
| Clean manual + unattended deny | blocked | permitted |
| Profile dotenv enables YOLO | permitted | permitted |
| Project dotenv enables YOLO, profile dotenv absent | permitted | permitted |
| Managed dotenv enables YOLO | permitted | permitted |
| Profile approval mode off | permitted | permitted |
| Profile unattended mode approve | permitted | permitted |
| Saved-session YOLO restored | permitted | permitted |
| Managed manual config + saved-session YOLO | permitted | permitted |
| Managed false/manual overrides profile YOLO; no saved YOLO | blocked | permitted |
| Same managed restriction + saved-session YOLO | permitted | permitted |
| Approval config changed to off after approval module import | permitted | permitted |

The guarded code was an inert print; the terminal strings were an inert
`chmod 777` example and `printf`. **None was dispatched or executed.** Only the
fixture session/config data was written.

Reproduce using the dependencies in `tests/requirements.txt`:

```sh
python tests/probe_child_approval_controls.py /absolute/hermes-source
```

Raw `decision-probe.json` is retained in the local investigation evidence packet;
it is not a runtime dependency.

## Why a separate profile is not a drop-in fallback

A new profile owns a different session database. The probe confirms its fresh
database does not contain the existing target. Hermes profile cloning explicitly
excludes `state.db` and session history. Routing messages to new conversations
would change destinations and continuity, not merely child approval settings.
Copying/sharing the original database is not a solution: it retains the saved
YOLO state and introduces concurrent-history ownership questions. Clearing the
saved bit in the original database would change interactive-session policy.

A dedicated restricted agent/profile remains possible as a **separate product
choice**, with explicit new destinations and credential/plugin setup; it is not
implemented or qualified here. Parent-YOLO refusal alone would not cover the
demonstrated profile/session bypasses. The later owner decision above disables
headless entirely pending a supported control; it does not inspect parent policy.

## Concrete upstream enhancement contract (proposal, not existing functionality)

Provide a supported launch-time restriction for an isolated child that:

1. Becomes authoritative before plugin/tool discovery and persists for the whole
   child lifetime. Configuration, dotenv, session resume/compression, `/yolo` and
   mode changes cannot weaken it. A failure to establish it prevents service
   readiness; it must not degrade into ordinary unrestricted service.
2. Retains the selected profile, credentials, plugins and original session IDs,
   without writing changed approval policy or YOLO state into that profile.
3. Applies consistently to terminal, execute-code and generic tool approval
   gates, including delegated execution. Provider-native execution routes must
   either support the restriction or be explicitly unavailable in that child.
4. Treats actions needing approval as blocked when no approver exists. Neither
   Smart auto-approval nor inherited approval caches silently provide consent.
   The contract must explicitly define which operator-configured permanent
   allowlists remain authoritative; this cannot be left implicit.
5. Leaves ordinary permitted work working and leaves an unrestricted interactive
   process unchanged. This is an approval control, **not** an OS sandbox or a
   guarantee against trusted same-user code modifying the runtime.
6. Exposes its effective restriction through a documented readiness/capability
   response, so Antenna can require a supporting runtime without guessing from
   a version string or silently falling back on an unknown flag.

No flag spelling is prescribed as an existing command. No upstream patch, issue
or comment was submitted. A host implementation needs upstream design agreement
and tests; this investigation does not assert that a tiny flag alone is enough.

### Required end-to-end proof after implementation

Drive the actual isolated `hermes serve` HTTP/WebSocket `session.resume` →
`prompt.submit` path, preferably using a deterministic local model fixture.
Request approval-gated operations on disposable sentinel files, verify those
files never change without approval, and verify ordinary permitted work does
change its separate sentinel. Repeat across parent YOLO, profile/project/managed
dotenv, off/Smart/unattended-approve config, saved YOLO, reloads, resume/compression
and delegated/provider-native paths. Also verify profile and interactive-session
policy bytes remain unchanged. The decision probes above do **not** satisfy this
gate; no actual serve turn was run in this investigation.

## Historical optional-app check

Follow-through: local 1.7.0 Diagnostics and Migration candidates now accept this
policy. Their CLI and extracted-package tests verify file-reference preservation,
private-file refusal and no credential disclosure. Published 1.6.9 readers remain
incompatible; use only a matching qualified app. The details below record the
original finding, not the current candidate status.

A disposable `bearerFile`-only policy is accepted by this candidate's validator.
Both separately shipped app validators reject it with `receiver and private
bearer required`:

- Diagnostics source: `7d512f65e9ae8506ba75384bc63a3084746faeb1`.
- Migration source: `7fd160e4a03d977aecbf71eb7cd2cc6bfc80c0b5`.

This is a confirmed reader-compatibility gap, not full CLI qualification. No app
source or user policy was changed; the check created no inbox/replay files. Fix
in the apps' authoritative repositories and refresh their helper provenance and
packages, rather than restoring inline secrets to satisfy old readers.

Reproduce with `node tests/probe_optional_app_policy.mjs /path/to/diagnostics-repo
/path/to/migration-repo` (one command line). The current probe asserts all three candidate readers accept the file-backed
policy; the original characterization expected the old readers to reject it.

Native install/update/remove/reinstall, full runtime delivery, encrypted age CLI
and final-byte scans remain in H170-010; this investigation does not close them.
