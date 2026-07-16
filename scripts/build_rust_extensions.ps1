param(
    [switch]$Release
)

$ErrorActionPreference = "Stop"
$crates = @("hal-core", "aether-runtime", "tensor-engine")
$feature = "python"
$profile = if ($Release) { "release" } else { "dev" }

foreach ($crate in $crates) {
    $cratePath = Join-Path $PSScriptRoot ".." $crate
    Write-Host "Building $crate ($profile) with feature '$feature'..."
    Push-Location $cratePath
    try {
        cargo build --features $feature --profile $profile
    } finally {
        Pop-Location
    }
}

Write-Host "All Rust extensions built."
