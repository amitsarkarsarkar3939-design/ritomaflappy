#!/usr/bin/env zsh
set -eu

SCRIPT_DIR=${0:A:h}
PYTHON=${PYTHON:-python3}

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    print -u2 "Python was not found. Install Python 3 or set PYTHON to its executable."
    exit 127
fi

exec "$PYTHON" "$SCRIPT_DIR/terminal.py" --cli "$@"
