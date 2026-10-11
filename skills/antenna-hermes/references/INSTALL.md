# Install Antenna for Hermes 1.6.9

This skill is instructions only. Install the native plugin separately, only when
the operator requests installation. Do not enable, pair, grant permissions, send
messages or install optional apps merely because the skill was loaded.

1. Select an explicit absolute `HERMES_HOME` for the intended profile. Prerequisites
   and full setup are in the [official User Guide](https://github.com/ClawReefAntenna/antenna-hermes/blob/v1.6.9/references/USER-GUIDE.md).
2. Download `antenna-hermes-1.6.9.git.bundle`, `manifest.json`, and `SHA256SUMS` from
   the [official v1.6.9 release](https://github.com/ClawReefAntenna/antenna-hermes/releases/tag/v1.6.9).
   Verify each downloaded asset against its exact checksum entry. A checksum file
   may also list the archive; either download that asset or explicitly account for
   its absence rather than treating a missing-file check as success.
3. Clone the verified bundle into a new directory and inspect its revision:

   ```sh
   git clone /absolute/downloads/antenna-hermes-1.6.9.git.bundle /absolute/antenna-hermes-source
   git -C /absolute/antenna-hermes-source rev-parse HEAD
   ```

   Expected scoped package commit: `4deb737fa6ad4a442a72077d1113ce564b196f85`.
   Do not install an unverified default-branch checkout as this pinned release.
4. Install disabled using native Hermes lifecycle:

   ```sh
   HERMES_HOME=/absolute/hermes-profile hermes plugins install file:///absolute/antenna-hermes-source --no-enable
   ```

   Review native scanner findings. A prior test-profile override is not permission
   to override a new installation; do not add `--force` or disable scanning silently.
5. Verify `<HERMES_HOME>/plugins/antenna/plugin.yaml` and read the installed
   `references/USER-GUIDE.md`. Complete identity, private configuration and explicit
   permission setup before enabling. Pairing does not grant message permissions.
   Use the installed guide for private contact exchange and a user-authorized test.

## Optional apps — GitHub only

- [Diagnostics Kit](https://github.com/ClawReefAntenna/antenna-diagnostics-hermes/releases/tag/v1.6.9)
- [Antenna Migration](https://github.com/ClawReefAntenna/antenna-migration-hermes/releases/tag/v1.6.9)

Neither is necessary for ordinary messaging. Extract their runtime archives into
separate directories, never over the plugin. Developer source bundles are not
runtime kits. Neither app has a separate Hermes Skills Hub entry.
