# Antenna for Hermes 1.7.0 — verification scope

The release retains the runtime code reviewed at
`0d53a5bd22934b9d0347070b9215f80ccdec8521`; release changes concern documentation
and package contents, not runtime behavior.

## Verified behavior

- 63 Python regression tests and five Node tests cover target-policy refusal,
  receipts, profile locks, storage, framing, host boundaries, signed ingress,
  managed-child lifecycle and inactive fresh registration.
- Four extracted-package actual-server cases cover non-YOLO delivery and
  saved-YOLO refusal on Hermes revisions `36592bb75c5f636b96408ca2e1bfad722bc3e7b1`
  and `00e5cf64a829232a6daceb3a8ad327106e56fe08`.
  Normal targets received messages; native approval blocked the fixture command
  without an approval response. Saved-YOLO targets were refused before model turns.
- Stock Plugin Doctor passed with four hooks on the extracted package.

[Version-scoped evidence and fixture results](https://github.com/ClawReefAntenna/antenna-hermes/tree/f3d7ac48eea4e949221a3338bb436874ff1fb90b/review-evidence/2026-10-13)
remain available for independent review.

## Limits

Actual-server cases used a deterministic loopback model and disposable profiles.
The harness started the server and receiver directly with the production child
environment builder; supervisor lifecycle was tested separately with a fake
backend. Parent YOLO was an environment fixture, not an interactive-parent UI test.
These results do not establish behavior on every Hermes version or provider.

The delivery-time YOLO check is not continuous monitoring or an atomic policy
lock. Interactive approval policy is unchanged. Optional apps are separately
versioned; their published 1.6.9 policy readers are incompatible with `bearerFile`.
Historical recovery and native lifecycle results apply to their recorded revisions,
not a claim that every lifecycle scenario was repeated for this release.
No completed paid AI-assisted scan is claimed for this runtime revision.

## Reproduce

From the source archive, install `tests/requirements.txt` in an isolated environment:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/delivery.mjs tests/framing.mjs tests/headless-unavailable.mjs
```

Tests and build tooling stay in source; the runtime archive excludes them.
Build with `python3 packaging/build.py --output /new/build-directory` from a clean
committed checkout. Per-file manifests and checksums accompany the release assets.
