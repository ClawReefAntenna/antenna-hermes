# Antenna 1.7.0 candidate: review evidence

Tested source: [`0d53a5bd22934b9d0347070b9215f80ccdec8521`](https://github.com/ClawReefAntenna/antenna-hermes/commit/0d53a5bd22934b9d0347070b9215f80ccdec8521).
This evidence-only branch does not change the tested candidate or its catalog pin.

## Packaged real-server results

| Hermes revision | Non-YOLO target | Saved-YOLO target |
| --- | --- | --- |
| `36592bb75c5f636b96408ca2e1bfad722bc3e7b1` | HTTP 202; native terminal approval timed out; action did not run | HTTP 503; `headless_yolo_target`; zero model requests/messages |
| `00e5cf64a829232a6daceb3a8ad327106e56fe08` | HTTP 202; native terminal approval timed out; action did not run | HTTP 503; `headless_yolo_target`; zero model requests/messages |

Full fixture results: [installed revision](installed-results.json), [reviewed revision](reviewed-results.json).
Both use parent `HERMES_YOLO_MODE=1`, production child environment value `0`, and no `--yolo` flag. All four disposable marker files remained mode 0600.

Native terminal result excerpt (both normal cases):

```text
status: blocked
exit_code: -1
user_summary: No answer within 5 seconds — the command did not run.
```

The harness exercised the extracted final archive, signed peer HTTP ingress, unmodified Hermes serve, public session APIs and native terminal approvals with a deterministic loopback model. The model requested a harmless chmod of a disposable marker file. Parent YOLO was simulated through environment settings, not an interactive-parent UI. Server and receiver were started directly with the production child-environment builder; supervisor lifecycle is separately fixture-tested. These results are revision-scoped, not a claim about untested Hermes versions or every profile configuration.

## Other verification

- 63 Python tests passed; five Node tests passed. Tests cover target and resumed-policy refusal before prompt submission, receipts/replay, lineage, locks, storage, host boundaries, registration and supervisor lifecycle. Fake backends are used in supervisor tests.
- Stock Plugin Doctor passed on the extracted runtime: manifest parsing, import and registration; zero tools and four hooks. This is registration verification, not a live-delivery test.
- Runtime and source archives rebuilt byte-for-byte; 82 extracted files matched the manifest. [Artifact verification](artifact-verification.json).
- Runtime SHA-256: `b5dae7a537f14cb3b57d7aa25d0a63c8d6cb272f9fb2a9cb199e76311df9675d`.

Regression commands at the tested source, with its test dependencies installed:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/delivery.mjs tests/framing.mjs tests/headless-unavailable.mjs
```

Earlier optional-app, encrypted-recovery and native replacement/TUI results remain tied to their recorded revisions; they were not rerun against this candidate. No completed paid core AI scan is claimed. Optional companion-dispatcher pruning remains uncompleted. This handoff is for review, not a release or deployment.
