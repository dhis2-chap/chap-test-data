# Shared by the scripts in this folder: source it, then call show before running a command.

# Print a command to stderr as "$ command args", quoting arguments that need it, so the scripts'
# own output on stdout stays clean.
show() {
  local out="$" arg
  for arg in "$@"; do
    if [[ $arg =~ ^[A-Za-z0-9_@%+=:,./-]+$ ]]; then out+=" $arg"; else out+=" '${arg//\'/\'\\\'\'}'"; fi
  done
  printf '%s\n' "$out" >&2
}
