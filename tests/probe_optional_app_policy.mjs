// Verify candidate app readers; CLI and extracted-package tests live in each app.
// Usage: node tests/probe_optional_app_policy.mjs DIAGNOSTICS_REPO MIGRATION_REPO
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const candidate = fileURLToPath(new URL('..', import.meta.url));
const [diagnostics, migration] = process.argv.slice(2);
assert(diagnostics && migration, 'Pass both optional-app repository paths');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ant-app-policy-'));
try {
  const secret = path.join(root, 'receiver-bearer');
  fs.writeFileSync(secret, 'fixture-only-' + 'x'.repeat(40), {mode: 0o600});
  const policy = {schemaVersion: 2, receiver: 'fixture', bearerFile: secret,
    mcs: 'dumb', inbox: 'on', peers: {}, destinations: {},
    inboxFile: path.join(root, 'inbox.json'), replayFile: path.join(root, 'replay.json')};
  const results = {};
  for (const [name, base] of Object.entries({candidate, diagnostics, migration})) {
    const {validateConfig} = await import(pathToFileURL(path.resolve(base, 'plugin/policy.mjs')));
    try { validateConfig(policy); results[name] = 'accepted'; }
    catch (error) { results[name] = error.message; }
  }
  assert.equal(results.candidate, 'accepted');
  assert.equal(results.diagnostics, 'accepted');
  assert.equal(results.migration, 'accepted');
  assert.equal(fs.readdirSync(root).length, 1);
  console.log(JSON.stringify({results, stateFilesCreated: false}));
} finally { fs.rmSync(root, {recursive: true}); }
