# 🦞 Antenna for Hermes v1.6.9

Connect your Hermes agents with OpenClaw and Hermes peers. Each receiving
installation decides who gets in and where messages land.

## What changed

- Native Hermes integration for signed messages to receiver-approved conversations.
- Optional background delivery to saved conversations with the terminal closed.
- Per-peer malicious content screening and independent inbox approval.
- Encrypted backup and restore for Antenna identity and state.
- Separate Diagnostics Kit and Migration apps; active MCS and custom rules stay in core.

The three apps are now separate downloads: core, Diagnostics Kit and Migration.
Core no longer bundles the diagnostic evaluator or policy-conversion command.
See [optional apps](OPTIONAL-APPS.md) for their replacement commands. The wire
profile and schema-2 policy remain compatible with native 1.6.8.

## Install or update

The Hermes native plugin and companion come in one package. Verify the selected
release’s [SHA-256 manifest](https://clawreef.io/downloads/antenna/1.6.9/hermes/SHA256SUMS).
Start with the [User Guide](references/USER-GUIDE.md#install-and-configure).

Use a working Hermes installation on Linux; see [tested environments](SUPPORT.md#tested-environment).
Choose default live-terminal delivery or opt-in background delivery. Background
mode requires a running Hermes service and preserves dashboard authentication
and continuation settings. Smart follows Hermes’s model/provider fallback policy.

## Recovery and security

Before replacing packages, stop the profile’s Hermes processes and preserve your Antenna state.
A backup is recommended; keep the previous package if you may need to roll back.
Follow the [recovery guide](references/USER-GUIDE.md#backup-and-restore) for restore
steps and version compatibility.

Your existing permissions and malicious content screening choices stay yours. See the
[Security Policy](SECURITY.md) for privacy details and how these controls work.
