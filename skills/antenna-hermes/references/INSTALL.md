# Antenna for Hermes 1.7.0 candidate installation

This Hub skill is instructions only. No 1.7.0 release artifact or immutable source
pin is published yet. Do not install the published 1.6.9 package and call it 1.7.0.
Do not install, enable, pair, grant permissions or send messages merely because
this skill was loaded.

For explicitly authorized disposable qualification only:

1. Select an absolute `HERMES_HOME` and a reviewed candidate source root.
2. Read its `QUALIFICATION-V170.md` and `references/USER-GUIDE.md`.
3. Use native `hermes plugins install file:///absolute/reviewed-source --no-enable`.
   Review scanner findings; do not add `--force` or disable scanning.
4. Verify `plugin.yaml` says `antenna`, version `1.7.0`. Prepare the private
   persistent data directory and explicit policy with the bundled guide.
5. Do not use a production profile until all release gates are closed.

The existing Diagnostics Kit and schema Migration app are separate 1.6.9 products;
compatibility with `bearerFile` requires qualification. Neither is needed for
normal core messaging or the new core `storage migrate` command.
