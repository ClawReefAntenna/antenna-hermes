#!/usr/bin/env bash
# Hermes companion dispatch; retained commands keep their v1.7.0 arguments.
set -euo pipefail
REAL_PATH="$(readlink -f "$0")"
ROOT="$(dirname "$(dirname "$REAL_PATH")")"
HOST_CONFIG="${ANTENNA_HOST_CONFIG:-${HERMES_HOME:-$HOME/.hermes}/config.yaml}"
export ANTENNA_HOST_CONFIG="$HOST_CONFIG"
command="${1:-help}"
shift || true
case "$command" in
  storage) exec python3 -B "$ROOT/scripts/antenna-storage.py" "$@" --host "$HOST_CONFIG" ;;
  mcs) echo 'Use the separate Antenna Diagnostics Kit for Hermes: node diagnostics/cli.mjs CONFIG_YAML test|evaluate ...' >&2; exit 1 ;;
  migrate) echo 'Use separate Antenna Migration for Hermes: node migration/cli.mjs CONFIG_YAML [NEW_POLICY_JSON | --apply]' >&2; exit 1 ;;
  doctor|readiness)
    if [[ ${1:-} == --gateway && $# == 2 ]]; then HOST_CONFIG="$2";
    elif [[ $# != 0 && "$*" != --json ]]; then echo 'Usage: antenna doctor|readiness [--gateway CONFIG_YAML] [--json]' >&2; exit 64; fi
    exec node "$ROOT/plugin/migration-check.mjs" doctor "$HOST_CONFIG" "$(python3 -B "$ROOT/hermes/storage.py" "$HOST_CONFIG")" ;;
  status) exec node "$ROOT/plugin/cli.mjs" "$HOST_CONFIG" status "$@" ;;
  backup)
    for option in "$@"; do
      if [[ "$option" == --host || "$option" == --host=* ]]; then
        exec python3 -B "$ROOT/scripts/antenna-backup.py" "$@"
      fi
    done
    exec python3 -B "$ROOT/scripts/antenna-backup.py" "$@" --host "$HOST_CONFIG" ;;
  setup|upgrade|pair|uninstall|model|test|test-suite|inbox)
    echo 'Retired v1.7.0 legacy operation. Use native Hermes plugin lifecycle, plugin/pairing.mjs, and antenna-plugin CONFIG_YAML inbox/check/select instead.' >&2; exit 1 ;;
  peers)
    if [[ ${1:-} == exchange ]]; then echo 'Legacy exchange is retired. Use plugin/pairing.mjs export/import.' >&2; exit 1; fi ;;
  config)
    if [[ ${1:-} == set && ${2:-} == relay_agent_model ]]; then echo 'The plugin has no relay model. Use antenna-plugin CONFIG_YAML select MODEL.' >&2; exit 1; fi ;;
  help|-h|--help)
    cat <<'EOF'
Antenna for Hermes v1.7.0
  antenna send|msg PEER [OPTIONS] MESSAGE
  antenna peers list|add|remove|test ...
  antenna sessions list|add|update|remove ...
  antenna config show|set KEY VALUE
  antenna groups ... | clawreef ... | log ...
  antenna status | doctor | readiness
  antenna backup create|inspect|verify|restore ...

Set HERMES_HOME or ANTENNA_HOST_CONFIG to select the native profile.
Use antenna-plugin CONFIG_YAML for policy, Smart selection, and inbox operations.
Contact exchange: node plugin/pairing.mjs export ROOT CONFIG_YAML PRIVATE_FILE
                 node plugin/pairing.mjs import ROOT PRIVATE_FILE PEER TARGET
Contact import and companion sessions edits do not grant plugin inbound authority.
Use native Hermes plugins install/enable/disable/remove for program lifecycle.
EOF
    exit 0 ;;
esac
exec bash "$ROOT/bin/antenna-companion.sh" "$command" "$@"
