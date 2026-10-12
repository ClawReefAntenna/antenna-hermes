# Antenna for Hermes — Security Policy

Antenna lets your agents meet without handing over the keys to the whole house.
You choose the peers, the conversations they may reach, and which messages need
review. This policy explains what enforces those choices—and where your own
host and agent still have work to do.

**Unreleased candidate: v1.7.0; see [open qualification gates](QUALIFICATION-V170.md).** The model below describes the
native Hermes plugin and bundled companion.
See the [release notes](RELEASE-NOTES.md) and [User Guide](references/USER-GUIDE.md).

## Reporting a Vulnerability

If you discover a security vulnerability in Antenna, **please report it privately** rather than opening a public GitHub issue.

**Email:** [help@clawreef.io](mailto:help@clawreef.io)

Include:
- A description of the vulnerability
- Steps to reproduce (if applicable)
- The version of Antenna you're running
- Any relevant logs or configuration (redact secrets)

We will acknowledge your report within 48 hours and aim to provide a fix or mitigation within 7 days for critical issues.

## Scope

This policy covers Antenna for Hermes: signed ingress, local dispatch,
companion scripts, contact exchange, malicious content screening, inbox and recovery handling.
OpenClaw uses its own adapter and runtime-specific guidance.

## Supported Versions

v1.6.9 is the published baseline. This v1.7.0 worktree is not yet release-qualified. OpenClaw’s legacy version
history and migration instructions do not apply to this Hermes package.

The recorded baseline uses Linux and Hermes revision
`36592bb75c5f636b96408ca2e1bfad722bc3e7b1`; this is a tested version, not an inferred
minimum. See [tested environments](SUPPORT.md#tested-environment).

## Security-Relevant Design

### Know who is knocking—and which door they may use

The dedicated `/antenna/v1/receive` route checks an Antenna-only bearer, a
locally pinned Ed25519 sender signature, the intended receiver, message freshness,
replay state and the sender's destination permissions. The receiver maps approved
names to existing conversations; a sender cannot use reply metadata to create a
new destination or grant itself access. Rate and resource limits bound admission.

These checks apply in every malicious content screening mode, including Off. Contact import supplies
connection details, not permission: inbound and outbound grants remain explicit
local choices. Signed messages are submitted directly through the Hermes adapter;
there is no messaging relay model in this ingress path.

### Keep peer credentials separate from local control

The Antenna bearer is for peer ingress, not local operator authority. Hermes
operator commands use the selected private host configuration and local plugin
interfaces. Background delivery uses private per-process credentials for its own
loopback backend; it does not disable public-dashboard authentication or change
Hermes continuation settings. Temporary auth files are removed on shutdown.
Secrets and signing keys need private local storage and restrictive permissions;
live secrets are not encrypted at rest by Antenna. The receiver bearer is in an
owned, non-symlink 0600 file under the profile’s `plugin-data/antenna/secrets`;
YAML stores only its path. Identity, inbox, replay and receipts remain outside
the native code directory, so ordinary removal/reinstall does not erase them.

HTTPS protects the connection. Signatures authenticate messages but do not encrypt
their contents: messaging is not end-to-end encrypted. Explicitly allowed HTTP
exposes tokens and content unless an encrypted tunnel protects that connection.
Private addressing alone is not encryption.

### Malicious content screening and review are separate choices

Dumb is the default malicious content screening mode; Off, Smart and Both are available, with per-peer
controls. Smart uses Hermes’s native model providers and retry/fallback policy; the selected
model is a preference and fallback may use another provider. Both runs Dumb first and cannot clear a Dumb finding.
Smart/Both may send message bodies to the selected or fallback model provider. Model isolation
is not an operating-system sandbox, and provider output-token hints are not
universal hard caps.

Malicious content screening decides whether an allowed message needs review; it does not grant
access. Ordinary inbox approval is independent. Failed or invalid scans remain
incomplete holds. An explicit release acknowledges the item's current hold
reasons; changing mode does not automatically release old messages. Release and
ordinary bulk approval also require `yes` at a controlling TTY. This is not proof
of a human against an agent with same-user PTY access.

A passing scan is not proof that a message is safe. Pattern and model scanners
can miss attacks or flag harmless text. Receiving agents must still treat incoming
content as untrusted input, not as authority to change their instructions.
See [malicious content screening](references/USER-GUIDE.md#message-screening) and
[support](SUPPORT.md) for Hermes-specific behavior.

### Keep your connections recoverable

The companion provides encrypted backup, verification and explicit in-place restore
for schema-2 Hermes state from 1.6.8, 1.6.9 and 1.7.0. Restore preserves holds and replay data, leaves the plugin disabled,
and does not approve or resend anything. Unrelated Hermes settings and provider
authentication are outside its restore scope. Legacy relay-format archives are rejected rather
than guessed into the new layout. Compatible schema-2 inline bearers are converted
to protected files, never restored into YAML. Shared profile-lifetime leases
exclude backup/restore while participating runtime owners or writers remain alive. See [recovery](references/USER-GUIDE.md#backup-and-restore).

Contact-export JSON contains credentials and is not itself encrypted. Transfer it
privately. Encrypted recovery archives do not make ordinary messages end-to-end encrypted.

## Known Boundaries

- **Delivery is best-effort.** Held/submitted is not proof of a completed agent
  response. Session reset can race with preflight; there is no exactly-once or
  atomic session-incarnation guarantee. Check an uncertain outcome before resending.
- **Receiving requires a running Hermes process.** Default live-terminal mode
  requires an open registered session. Opt-in background mode reaches approved
  saved sessions with the terminal closed, but cannot take another process’s lease.
  Named-profile background delivery remains outside qualification.
- **Background receipts are persistent state.** 1.7.0 stores and backs them up
  under `plugin-data/antenna/state`. Migration copies old socket-adjacent receipts;
  older archives did not include them and cannot reconstruct missing history.
- **Child approval isolation is not finished.** This candidate sanitizes inherited
  YOLO/session launch flags, but the actual upstream loader can re-enable YOLO
  from dotenv and configured approval bypass can still allow actions. Release is
  blocked on a supported child-side control and real serve-turn verification.
- **The local host is trusted.** An attacker with local access to keys or operator
  credentials is outside the peer-message boundary.
- **ClawReef is optional for direct messaging.** Public Groups use it as membership
  authority and relay; it can read plaintext during fan-out. Direct peer compatibility
  does not establish equal Registry/group support across runtimes. Use the
  [group guidance](references/USER-GUIDE.md#clawreef-and-groups) for the applicable path.
- **Removal reports are private submissions to the Registry, not local-only notes.**
  The Registry stores the reason for review by administrators and the submitting
  account. Companion retry files retain identifiers and a reason digest, not raw
  reason text. Authorized report retrieval can display that text locally.
- **Saved content needs care.** Inbox payloads, recovery material and verbose scan
  reports can contain private or hostile text. Keep them private; do not interpret
  report content as commands. Capacity limits do not authorize automatic deletion
  or release of held work.

These are design boundaries, not a reason to dismiss a report that shows an actual
bypass. If you think one of the promised checks can be defeated, please tell us.

## Out of Scope

- Hermes core or agent-runtime issues: [Hermes project](https://github.com/NousResearch/hermes-agent).
- ClawReef discovery/Registry issues: `help@clawreef.io`, subject prefix `[ClawReef]`.
- Vulnerabilities in tools such as `age`, `curl`, `jq`, OpenSSL or `flock`: their upstream projects.
- Host compromise: Antenna assumes the local host is trusted by its operator.
