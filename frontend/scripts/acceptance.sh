#!/bin/sh
set -e
PW_SRC="${NODE_PATH:-}/@playwright/test"
if [ -z "${NODE_PATH:-}" ] || [ ! -d "$PW_SRC" ]; then
  PW_SRC="$(dirname "$(dirname "$(readlink -f "$(command -v playwright)")")")/lib/node_modules/@playwright/test"
fi
mkdir -p node_modules/@playwright
ln -sfn "$PW_SRC" node_modules/@playwright/test
exec playwright test -c tests/acceptance/playwright.config.ts "$@"
