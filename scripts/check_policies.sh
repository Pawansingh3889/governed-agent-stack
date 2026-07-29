#!/usr/bin/env bash
# Run the stack's governance policies against stack.yaml.
# Skips cleanly (exit 0) if conftest isn't installed, so it never blocks a checkout
# that just wants to read the docs.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v conftest >/dev/null 2>&1; then
  echo "conftest not found — skipping policy checks."
  echo "Install it to run them: https://www.conftest.dev/install/"
  exit 0
fi

echo "Running governance policies against stack.yaml..."
conftest test stack.yaml --policy policies/
