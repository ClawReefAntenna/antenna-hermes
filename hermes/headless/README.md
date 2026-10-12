# Background delivery — disabled in the 1.7.0 candidate

Headless startup and submission are unavailable until Hermes provides a supported,
verified child-only approval control. This is a fixed compatibility boundary, not
a new approval-policy system or a user-configurable override.

## What remains available

Live-session signed delivery and held-message release use the existing live socket
adapter. Keep the approved destination open and registered. Interactive YOLO and
that session’s normal approval policy are unchanged. Saved `headless.enabled: true`
settings are retained, but the receiver logs the limitation and starts only the
normal live receiver. A closed or unregistered destination remains unavailable.

No profile, dotenv, saved-session policy or provider setting is rewritten. Neither
turning YOLO off nor an old `headless-active.json` pointer enables a backend.
Direct supervisor, bridge CLI/library submission and Node headless adapter entry
points refuse before backend launch or prompt submission. Unavailable means no
submission was attempted, not an uncertain receipt requiring a blind retry.

## Re-enabling

Use the [Hermes-owned control contract](../../CHILD-APPROVAL-INVESTIGATION.md).
Hermes must enforce the restriction for the child lifetime and report it through
a supported capability/readiness response. Only then can Antenna add the small
launch/compatibility integration and run the specified actual-server tests.
Do not patch private Hermes APIs or build configuration/session watchers here.

The earlier supervisor and bridge transport logic remains for future integration
and fixture regressions, but production admission is disabled. Receipt tests
explicitly mock admission only with fake HTTP/WebSocket transports. They are not
approval-isolation or server-turn proof. Historical 1.6.9 canary results do not
qualify this candidate. Persistent receipts remain part of storage/recovery.

See [candidate qualification](../../QUALIFICATION-V170.md) for checks and open gates.
