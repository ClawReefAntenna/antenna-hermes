# Opt-in background delivery

Headless delivery is available for explicitly granted **non-YOLO targets**.
YOLO-enabled targets are refused; interactive YOLO is unchanged.

## Configuration

Configure `headless` under the native Antenna plugin settings with `enabled: true`,
absolute `python` (with httpx/websockets), `hermes` executable and profile `home`
paths, an unused loopback backend `port`, and `grants` mapping peer IDs to exact
`agent:main:<session-id>` destinations. The home must match the owning profile.
For example (replace paths, port and target with your installation):

```yaml
headless:
  enabled: true
  python: /absolute/hermes-venv/bin/python
  hermes: /absolute/bin/hermes
  home: /absolute/hermes-profile
  port: 18991
  grants:
    trusted-peer: ["agent:main:session-id"]
```

Normal peer/destination permissions and receive checks still apply. Restart the
profile after configuration. Disable headless to select live-session delivery.
Expose only the peer HTTPS route, never the private backend. The supervisor starts
loopback `hermes serve --isolated`, sanitizes child bypass variables and creates
ephemeral authentication credentials. Parent exit stops the managed children.
Persistent delivery receipts remain under profile-owned Antenna state.

## Target check

The bridge resolves the existing compression lineage and reads the final target's
`model_config.yolo_mode` through public session detail. A saved-YOLO target is
refused before resume. It then resumes with `eager_build: true` and requires
`info.yolo: false` before prompt submission. Missing or malformed policy responses
are unavailable. A YOLO ancestor does not disqualify a non-YOLO final target.

The bridge reports `headless_yolo_target` or `headless_target_policy_unavailable`;
peer ingress currently returns generic unavailable. Native Hermes approvals remain
in charge of tools. An unanswered approval can block the action even when the
message was delivered successfully.

This is a bounded check at delivery, not continuous monitoring, an atomic policy
lock or an approval-policy replacement. No Hermes code or saved settings are
modified. Live-session approval policy remains the operator's choice.

See [verification](../../VERIFICATION.md) for tested scope and limitations.
