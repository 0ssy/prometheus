#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-dev}"
FEATURE="python,c-hal"
CRATES=("hal-core" "aether-runtime" "tensor-engine")

echo "Building Zig hardware utilities..."
if command -v zig >/dev/null 2>&1; then
    pushd "zig" > /dev/null
    zig build
    popd > /dev/null
else
    echo "Warning: Zig not found on PATH; skipping Zig build"
fi

for crate in "${CRATES[@]}"; do
    echo "Building $crate ($PROFILE) with feature '$FEATURE'..."
    pushd "crates/$crate" > /dev/null
    cargo build --features "$FEATURE" --profile "$PROFILE"
    popd > /dev/null
done

echo "All Rust extensions built."
