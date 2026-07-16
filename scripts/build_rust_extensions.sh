#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-dev}"
FEATURE="python"
CRATES=("hal-core" "aether-runtime" "tensor-engine")

for crate in "${CRATES[@]}"; do
    echo "Building $crate ($PROFILE) with feature '$FEATURE'..."
    pushd "crates/$crate" > /dev/null
    cargo build --features "$FEATURE" --profile "$PROFILE"
    popd > /dev/null
done

echo "All Rust extensions built."
