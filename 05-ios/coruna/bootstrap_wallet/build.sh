#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if ! xcrun --sdk iphoneos --show-sdk-path >/dev/null 2>&1; then
  echo "[wallet_bridge] iOS SDK not found. Install Xcode + iPhone SDK to build wallet_bridge.dylib." >&2
  exit 1
fi
make clean all
echo "[wallet_bridge] OK -> payloads/wallet_bridge.dylib"
