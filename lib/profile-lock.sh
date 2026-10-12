#!/usr/bin/env bash
# Retained companion writers participate in profile-wide recovery exclusion.
_antenna_host="${ANTENNA_HOST_CONFIG:-${HERMES_HOME:-$HOME/.hermes}/config.yaml}"
case "$_antenna_host" in
  *.yaml|*.yml) ;;
  *) echo 'Hermes YAML host configuration required; foreign hosts are unsupported.' >&2; exit 1 ;;
esac
_antenna_profile="$(dirname "$(realpath -m "$_antenna_host")")"
_antenna_fd="${ANTENNA_PROFILE_LEASE_FD:-}"
_antenna_lock_match=''
if [[ "$_antenna_fd" =~ ^[0-9]+$ && "${ANTENNA_PROFILE_LEASE_HOME:-}" == "$_antenna_profile" ]]; then
  _antenna_lock_match="$(readlink "/proc/$$/fd/$_antenna_fd" 2>/dev/null || true)"
fi
if [[ "$_antenna_lock_match" != "$_antenna_profile/.antenna-profile.lock" ]]; then
  _antenna_code="$(dirname "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")")"
  exec python3 "$_antenna_code/hermes/profile_lock.py" "$_antenna_profile" -- bash "$(readlink -f "$0")" "$@"
fi

# Match Hermes public plugin_data_dir("antenna") for the selected profile.
SKILL_DIR="$(python3 -B "$(dirname "${BASH_SOURCE[0]}")/../hermes/storage.py" "$_antenna_host")" || exit 1
export ANTENNA_DATA_ROOT="$SKILL_DIR"

unset _antenna_host _antenna_profile _antenna_fd _antenna_lock_match _antenna_code
