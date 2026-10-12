# Optional apps for Antenna for Hermes

The core plugin and bundled companion handle everyday messaging, active Malicious
Content Scanning, inbox review, pairing, readiness and encrypted recovery.
Neither optional app is required to send or receive messages.

- [Antenna Diagnostics Kit for Hermes](https://github.com/ClawReefAntenna/antenna-diagnostics-hermes): evaluate sample/custom messages and
  rules, with the matching scanner helpers and bundled corpus. Run from its own
  extracted directory: `node diagnostics/cli.mjs CONFIG_YAML test|evaluate ...`.
- [Antenna Migration for Hermes](https://github.com/ClawReefAntenna/antenna-migration-hermes): preview/export or explicitly apply an
  existing schema-1 policy conversion. Run from its own extracted directory:
  `node migration/cli.mjs CONFIG_YAML [NEW_POLICY_JSON | --apply]`.

The existing kits are **1.6.9**. Their compatibility with the new `bearerFile`
policy is not yet qualified; do not use them to write a v1.7.0 policy until that
work is complete. They are separate from the core storage migration command. Install/extract the apps in
separate directories, never over the core plugin or each other. Core `mcs` and
`migrate` commands explain where the operations moved; they do not invoke another
installation. Active MCS mode/model/rules and inbox commands remain in core.

The Migration app does not support OpenClaw relay retirement or cross-runtime
conversation migration. See its guide for the Hermes-specific supported transition.
