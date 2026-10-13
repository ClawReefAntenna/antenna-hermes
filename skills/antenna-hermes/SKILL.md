---
name: antenna-hermes
description: Install or use Antenna for Hermes for signed peer messaging, pairing, held-message review, and recovery. Requires the separate native Antenna plugin; this skill alone does not enable messaging.
license: MIT
metadata:
  version: "1.7.0"
  author: ClawReefAntenna
  hermes:
    tags: [communication, antenna, hermes]
---

# Antenna for Hermes

Unreleased candidate. Read the verified installation’s `QUALIFICATION-V170.md`;
release qualification remains open. Headless delivery is opt-in and limited to non-YOLO targets. Do not deploy yet.

## Resolve the installation first

This is the standalone Skills Hub guide for Antenna **1.7.0**, not the plugin
installer or a background service. Installing this skill does not install, enable,
pair or configure Antenna. Never derive the plugin root from this skill's directory.

1. Select the intended Hermes profile explicitly. Use its `HERMES_HOME` (an
   absolute directory), or ask the operator to identify it if unclear. A separate
   `ANTENNA_HOST_CONFIG` selects a config file, not a different plugin code root;
   confirm both refer to the intended installation. Do not silently use another
   profile or assume a custom config lives next to the plugin.
2. The normal native plugin root is `<HERMES_HOME>/plugins/antenna`. Verify
   `plugin.yaml` declares `name: antenna` and `version: 1.7.0`, and that
   `bin/antenna.sh`, `bin/antenna-plugin` and `references/USER-GUIDE.md` exist.
   For a nonstandard location, require the operator's explicit plugin root and
   perform the same checks. Do not run commands from an unrelated PATH installation.
3. If the plugin is missing, use the [installation guide](references/INSTALL.md).
   If its version differs, read that installation's bundled guide/skill rather
   than assuming this version's commands apply. Stop here until a matching
   installation is verified. Installation must leave the plugin disabled for setup.
4. Use `<root>` below only for that verified plugin root. Read its
   `references/USER-GUIDE.md` before operating it. The plugin also supplies its own
   `antenna` skill; this Hub entry is named `antenna-hermes` so installation does not
   overwrite it. Both describe one installation, not two independent services.

## Operate the verified installation

1. Select the intended native profile with `HERMES_HOME` or
   `ANTENNA_HOST_CONFIG`; do not select a different installation.
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
   A human must confirm `yes` at a controlling terminal. Do not simulate that
   confirmation with piped input or an agent-created PTY.
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
   Store keys and state in `<HERMES_HOME>/plugin-data/antenna`, not the code root.
   Follow the guide’s stopped-profile storage migration before removing old code.
   Backup passphrases go directly into age's terminal prompt, never chat. Read
   the User Guide recovery section: a bare reinstall must first become a configured,
   stopped/disabled target; do not pair its placeholder identity. Restore without
   `--apply` is preview only. Application restores Antenna state, not host settings
   or Hermes history, and leaves Antenna disabled. Verify original identity/holds,
   explicitly enable/resume/register, then check Doctor and signed delivery without
   re-pairing. A disabled-plugin Doctor complaint before activation is expected.

## Runtime limits

Keep the target open and make a local turn after opening/resuming it. Headless
requires a non-YOLO target. Saved and effective YOLO state are checked before
submission; unverifiable policy is unavailable. Interactive YOLO is unchanged.
No Hermes patch or continuous monitoring is used.

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
