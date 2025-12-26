#!/usr/bin/env bash
set -euo pipefail

PREFIX="var/newman_deps"
echo "Installing Newman locally into ${PREFIX} (node_modules/.bin)..."
npm install --no-save --legacy-peer-deps --force --prefix "${PREFIX}" newman@6 newman-reporter-html newman-reporter-htmlextra
echo "✓ Newman installed. Version:"
PATH="${PREFIX}/node_modules/.bin:${PATH}" npx newman --version
