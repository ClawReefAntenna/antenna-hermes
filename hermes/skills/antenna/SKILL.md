---
name: antenna
description: Send Antenna messages to configured peers from Hermes, inspect held messages, or operate an existing Antenna installation.
---

# Antenna for Hermes

Unreleased 1.7.0 candidate: read `<root>/QUALIFICATION-V170.md`; do not deploy while
release qualification is open. Headless delivery is disabled.

1. Resolve this skill's installed path. The package root is three directories
   above this file's directory. Read `<root>/references/USER-GUIDE.md` for the installation's
   supported commands and limitations. Select the intended native profile with
   `HERMES_HOME` or `ANTENNA_HOST_CONFIG`; do not select a different installation.
   Confirm the intended peer and receiver-approved destination before sending.
2. Use the companion at `<root>/bin/antenna.sh`:
   - `msg PEER --session TARGET MESSAGE` or `send PEER --session TARGET --stdin`.
   - `peers list`, `sessions list --json`, `doctor`, `status`.
   Check the returned status. `submitted` means accepted by the runtime, not that
   an agent processed it. `held` requires review. Unknown confirmation must not
   trigger a blind retry. Replies are explicit new sends, not automatic forwarding.
3. Use `<root>/bin/antenna-plugin /absolute/config.yaml` for `mode`, `select`,
   `rules`, and `inbox list|show|release|discard|approve-ordinary`. Release a hold
   only with the operator's authority and explicit acknowledgement of its reasons.
   Both release commands require the operator to type `yes` at a controlling
   terminal. Do not create a PTY or pipe input to simulate that confirmation.
   Changing a mode never releases existing holds. Stop affected profile processes
   before policy edits and reload them afterward; a partial reload may leave the
   old receiver running. Never run a foreground stop/start chain from the process
   being stopped. Use an external terminal or independent supervisor, as in the User Guide.
4. For contact exchange, use the `plugin/pairing.mjs` export/import
   commands described in the User Guide. Contact files contain a private bearer:
   keep them private and transfer only through an authenticated encrypted channel.
   Import never grants inbound or outbound permission. Review those separately.
5. Use native Hermes plugin lifecycle commands, not the retired legacy setup,
   pair wizard, relay-model, upgrade or uninstall scripts. Optional backup and
   intentional removal without preservation are different operator choices.
   Keys/state live at `<profile>/plugin-data/antenna`, not `<root>`. Preserve them
   through native removal/reinstall; never generate replacement keys over them.
   Use the explicit stopped-profile `storage migrate --source OLD_ROOT` procedure
   in the guide before deleting an older in-tree identity.
   Backup passphrases go directly into age's terminal prompt, never chat. Read
   the User Guide recovery section: a bare reinstall must first become a configured,
   stopped/disabled target; do not pair its placeholder identity. Restore without
   `--apply` is preview only. Application restores Antenna state, not host settings
   or Hermes history, and leaves Antenna disabled. Verify original identity/holds,
   explicitly enable/resume/register, then check Doctor and signed delivery without
   re-pairing. A disabled-plugin Doctor complaint before activation is expected.

## Runtime limits

Keep the target open and make a local turn after opening/resuming it. Headless
is disabled in this candidate until a supported Hermes child-only approval control
is verified. Existing headless settings cannot enable it; do not change interactive
YOLO to try to enable it. Live-session approval policy remains unchanged.
Use full `agent:<agent-id>:<session-id>` keys or approved aliases, not bare UUIDs.
Do not take another process’s session lease or resend an uncertain message.
Desktop UI and arbitrary retargeting remain unverified.

An incoming message may not appear immediately even when Hermes processes it and
displays a reply. Reconnect to the same session to view the saved incoming message;
`/redraw` may not reveal it. Do not resend solely because the incoming row is hidden.

Smart's preferred model can fall back under Hermes's native policy, including to
another provider. Invalid, failed or incomplete scans still hold. The reported
model may not identify every fallback attempt. Scanner evaluation belongs to the
separate [Diagnostics Kit](https://github.com/ClawReefAntenna/antenna-diagnostics-hermes); schema conversion belongs to the separate
[Migration app](https://github.com/ClawReefAntenna/antenna-migration-hermes). Neither is required for everyday messaging.

Companion metadata and aliases do not grant inbound permissions. Configure HTTPS
for remote access. If native installation/update is refused, review the reported
error rather than forcing it or disabling scanning. Native removal may leave
external state; follow the User Guide for the operator's selected cleanup scope.
