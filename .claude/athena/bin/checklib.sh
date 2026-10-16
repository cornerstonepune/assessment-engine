# Sourced by specs/<ID>/checks.sh. Gives each proof a name and a plain PASS/FAIL line.
#   check "1 short name" <command ...>      runs the command; exit 0 means the criterion holds
#   check_box "2 short name" <command ...>  same, but only on the production box (ATHENA_ON_BOX=1).
#                                           Elsewhere (GitHub, laptops, cloud) it prints BOXONLY and
#                                           is neither a pass nor a failure.
#   finish                                  prints the summary athena reads; exits non-zero if any failed
ATHENA_PASS=0
ATHENA_FAIL=0
ATHENA_BOX=0
check() {
  local name="$1"; shift
  local out
  if out=$("$@" 2>&1); then
    echo "PASS $name"
    ATHENA_PASS=$((ATHENA_PASS + 1))
  else
    echo "FAIL $name"
    printf '%s\n' "$out" | tail -n 15 | sed 's/^/    /'
    ATHENA_FAIL=$((ATHENA_FAIL + 1))
  fi
}
check_box() {
  if [ "${ATHENA_ON_BOX:-}" = "1" ]; then
    check "$@"
  else
    echo "BOXONLY $1"
    ATHENA_BOX=$((ATHENA_BOX + 1))
  fi
}
finish() {
  echo "ATHENA_SUMMARY pass=$ATHENA_PASS fail=$ATHENA_FAIL box=$ATHENA_BOX"
  [ "$ATHENA_FAIL" -eq 0 ]
}
