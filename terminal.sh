#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PYTHON:-python3}

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    printf 'Python was not found. Install Python 3 or set PYTHON to its executable.\n' >&2
    exit 127
fi

exec "$PYTHON" "$SCRIPT_DIR/terminal.py" --cli "$@"
