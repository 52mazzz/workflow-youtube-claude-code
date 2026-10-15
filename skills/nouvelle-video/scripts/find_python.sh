#!/bin/sh
# Prints the first Python interpreter that actually runs. On Windows, `python` is often a
# Microsoft Store stub that exists on PATH but fails, so every candidate is executed, not just looked up.
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1; then
    echo "$c"; exit 0
  fi
done
for p in "$LOCALAPPDATA"/Programs/Python/Python3*/python.exe /usr/bin/python3 /opt/homebrew/bin/python3; do
  [ -x "$p" ] && "$p" -c "import sys" >/dev/null 2>&1 && { echo "$p"; exit 0; }
done
echo "no working python found" >&2; exit 1
