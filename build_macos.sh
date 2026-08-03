#!/usr/bin/env bash
# Build the native macOS application from this project folder.
set -euo pipefail

python3 -m pip install -r requirements.txt pyinstaller

# Create a macOS .icns icon from the supplied Monster logo.
rm -rf monster-logo.iconset monster-logo.icns
mkdir monster-logo.iconset
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" logo-clean.png --out "monster-logo.iconset/icon_${size}x${size}.png" >/dev/null
  doubled=$((size * 2))
  sips -z "$doubled" "$doubled" logo-clean.png --out "monster-logo.iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns monster-logo.iconset -o monster-logo.icns

python3 -m PyInstaller --noconfirm --clean --windowed \
  --name MonsterEnergyScreamChallenge \
  --icon monster-logo.icns \
  --add-data "logo-clean.png:." \
  soundboard.py

echo "macOS build created: dist/MonsterEnergyScreamChallenge.app"
