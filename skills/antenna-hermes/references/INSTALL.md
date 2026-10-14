# Antenna for Hermes 1.7.0 installation

This Hub skill is instructions only. Do not install, enable, pair, grant
permissions or send messages merely because this skill was loaded.

1. Select the intended absolute `HERMES_HOME` explicitly.
2. Download `antenna-hermes-1.7.0.tgz` and `SHA256SUMS` from the
   [v1.7.0 release](https://github.com/ClawReefAntenna/antenna-hermes/releases/tag/v1.7.0).
3. In a new download directory, run `sha256sum --check --ignore-missing SHA256SUMS`.
   Require an `OK` result for that runtime archive, then extract it with
   `tar -xzf antenna-hermes-1.7.0.tgz`.
4. Read the extracted `references/USER-GUIDE.md`. Install with
   `hermes plugins install file:///absolute/download-directory/antenna-hermes --no-enable`,
   substituting the actual absolute path. Review native scanner findings;
   do not add `--force` or disable scanning.
5. Verify `plugin.yaml` declares `antenna`, version `1.7.0`. Follow the guide
   to prepare private persistent storage and policy before explicitly enabling.
   Existing installations must follow its identity-preserving upgrade procedure.

The published Diagnostics Kit and schema Migration app are separate 1.6.9 products
and do not support the new `bearerFile` policy. Neither is needed for normal core
messaging or the core `storage migrate` command.
