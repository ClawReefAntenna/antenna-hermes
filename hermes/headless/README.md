# Background delivery — opt-in

**1.7.0 candidate: child approval isolation remains unqualified; do not deploy yet.**

This local candidate delivers already-authorized Antenna messages using the existing
Hermes HTTP/WebSocket APIs. It does not patch or import Hermes runtime internals.
The default receiver retains its existing live-session socket adapter.

The plugin now owns backend startup, readiness, private authentication, receiver
startup and bounded shutdown. Parent EOF (including parent death) stops both
children. The inherited receiver lease stays held until supervisor cleanup.
Unexpected child exit stops the service; automatic message resubmission is never
used. Reloading a plugin owner starts a new backend and retains receipt history.
No terminal window is required, but a background Hermes process loading Antenna
must remain running. Native background-host installation has passed on two Linux canaries.

Candidate settings under `plugins.entries.antenna.settings`:

```yaml
socket_dir: /short/private/as
listen_port: 18792
headless:
  enabled: true
  python: /absolute/bridge-venv/bin/python
  hermes: /absolute/bin/hermes
  home: /absolute/default-hermes-home
  port: 19387
  agent_id: main
  grants:
    paired-peer: ["agent:main:approved-stored-id"]
```

Use a Python environment containing `requirements.txt`; this environment is not
a Hermes runtime patch. The managed backend uses the supported `hermes serve
--isolated --host 127.0.0.1 --port ... --skip-build` interface. Its child plugin
receiver is suppressed to prevent recursive services. Both ports must be free.
The socket directory still needs to fit the operating system Unix-socket limit.

### Honor the user's Hermes continuation policy

Antenna does not require, override, or write `desktop.auto_continue.enabled`.
The managed backend uses the selected home's normal Hermes configuration and
Hermes's defaults when the setting is absent. Reopening a conversation may resume
interrupted work when Hermes's configured recovery rules allow it; if the user
has disabled auto-continuation, Hermes does not automatically continue that work.
These are Hermes semantics, not an Antenna-specific policy decision.

### Public-dashboard authentication compatibility

When the host's public dashboard configuration engages its authentication gate,
the managed private loopback backend now uses Hermes's supported password-login
and single-use WebSocket-ticket endpoints. Its supervisor supplies random
process-local Basic-provider credentials and a separate signing secret through
supported environment settings. It does not write those credentials to the host
configuration or modify the separately running public dashboard process.

The old session-token request is still rejected by the gate. The client removes
that old bearer header before cookie authentication, caches private cookies to
avoid repeated logins, and obtains a fresh short-lived ticket for each WebSocket.
Wrong credentials still fail. Ungated loopback hosts retain session-token auth.
No `HERMES_DESKTOP` exemption, auth disabling flag or runtime patch is used.

Install and update through the native Hermes plugin lifecycle and its reviewed
source pin. Preserve persistent data and follow the version-specific upgrade
instructions; this package provides no forced local reinstall helper.

Ephemeral token/config files are owned mode0600 under a mode0700 directory.
`headless-active.json` is a private owner-local pointer used by inbox approval;
it is removed on shutdown. Offline approval fails closed. Persistent receipt
history lives at `<HERMES_HOME>/plugin-data/antenna/state/headless-receipts.sqlite`.
The storage migration preserves the earlier socket-adjacent database. Shared
profile leases remain inherited by the supervisor, backend, receiver and bridge
until their actual exit; backup/restore require exclusive profile ownership.

A test embedding may still pass `options.headless = {python, config}` to
`receiver()` and `makeFlow()`. This lower-level harness does not supervise a
backend; normal managed operation supplies its config automatically.

Private JSON configuration example (all paths operator-supplied):

```json
{
  "origin": "http://127.0.0.1:19387",
  "token_file": "/private/hermes-session-token",
  "state_dir": "/private/antenna-headless-state",
  "agent_id": "main",
  "grants": {"paired-peer": ["agent:main:approved-stored-id"]}
}
```

Config and token must be owned regular files with mode0600; state directory must
be owned mode0700. Only explicit loopback IP origins are accepted. The candidate
is default-profile only. Antenna's existing signed ingress, grants, screening and
inbox remain the admission authority; these grants are an additional local bound,
not a replacement for authentication. Never expose the Python stdin interface to
remote peers or use it to bypass ReceiveFlow.

## Behavior

- Resolve performs authenticated read-only stored-session and lineage lookup.
- Accept only exact IDs and compression-parent edges; reject branch, delegate,
  reset, tool and cross-profile hops. Recheck resolved ID at resume/submission.
- Resume existing approved conversation, then submit with `queued:true`.
- Persist message identity before attempting delivery. Repeated IDs return stored
  outcome; changed payload under an existing ID is rejected.
- `submitted/runtime_persisted` means a user-row receipt, not a completed model turn.
- A queued response or lost acknowledgement remains `unknown`. A later identical
  request can reconcile an exact payload hash in the last500 history rows, without
  resubmitting. Failure to find a row is not permission to resend.
- Existing signed HTTP replay policy still rejects repeat envelopes. Journal
  reconciliation is currently an owner-local operation, not a new remote retry API.
- Keep explicit untrusted framing. Model refusal to act on peer instructions does
  not mean transport failed. Automatic outward replies are not added.

## Qualification and limits

The corrected candidate passed isolated gated-authentication, supervisor, receipt,
replay and lineage tests, then native background-host installation on two Linux
Hermes36592bb75 canaries. Both delivered signed messages to approved saved sessions
with the terminal closed, before and after restart. Original peer, authentication
and continuation settings were preserved. These are persisted-input checks, not
promises that model work finishes or that every possible conversation can be woken.

Still outside qualification: named-profile background delivery, attachment to another
process's active lease, natural model-triggered compression and reconciliation beyond
the latest500 history rows. Compression fixtures use Hermes's publication API;
only verified compression-parent edges are followed.

Run test_bridge.py, test_auth.py and test_managed.py with the pinned requirements.
Signed integration additionally needs a disposable real Hermes backend; never use a
production profile as a fixture. Package validation and scanner results are separate
from these runtime checks. This is a release candidate, not a published release.
