#!/usr/bin/env bash
set -euo pipefail

# Build macOS .app with py2app and optionally create a DMG.
# Usage: scripts/build_mac.sh
# Env vars:
#   APP_NAME (default: app)
#   DIST_DIR (default: dist)
#   CREATE_DMG (default: 1) set to 0 to skip

APP_NAME=${APP_NAME:-API Test Tray}
DIST_DIR=${DIST_DIR:-dist}
CREATE_DMG=${CREATE_DMG:-1}

python3 -m pip install -r requirements.txt
python3 -m pip install py2app

python3 setup.py py2app

APP_PATH="$DIST_DIR/${APP_NAME}.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "ERROR: App not found at $APP_PATH" >&2
  exit 1
fi

echo "Built: $APP_PATH"

if [[ "$CREATE_DMG" == "1" ]]; then
  DMG_PATH="$DIST_DIR/${APP_NAME}.dmg"
  echo "Creating DMG at $DMG_PATH"
  hdiutil create -volname "${APP_NAME}" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"
  echo "DMG created: $DMG_PATH"
fi

echo "Done."
