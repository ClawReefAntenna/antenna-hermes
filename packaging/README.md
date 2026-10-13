# Candidate build

Build the unreleased 1.7.0 Hermes plugin/companion from a clean committed checkout:

```sh
python3 packaging/build.py --output /new/build-directory
```

`allowlists.json` is the explicit installable payload. Tests and build scripts
remain in the developer source archive, not the runtime archive. Output includes
per-file hashes, source revision and a deterministic `.tgz`. The builder never
installs, publishes, tags or edits a live profile. Rebuild into a second new output
directory and compare archive hashes before scanning the exact prepared bytes.

Headless delivery is opt-in for non-YOLO targets. See [qualification](../QUALIFICATION-V170.md)
for current checks and release gates. Optional apps build in their own repositories.
