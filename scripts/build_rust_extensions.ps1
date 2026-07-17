param(
    [switch]$Release
)

$ErrorActionPreference = "Stop"
$crates = @("hal-core", "aether-runtime", "tensor-engine")
$feature = if ($Release) { "python,c-hal,full" } else { "python,c-hal" }
$profile = if ($Release) { "release" } else { "dev" }

Write-Host "Building Zig hardware utilities..."
if (Get-Command zig -ErrorAction SilentlyContinue) {
    Push-Location "$PSScriptRoot\..\zig"
    try {
        zig build
    } finally {
        Pop-Location
    }
} else {
    Write-Warning "Zig not found on PATH; skipping Zig build"
}

foreach ($crate in $crates) {
    $cratePath = Join-Path $PSScriptRoot ".." "crates" $crate
    Write-Host "Building $crate ($profile) with feature '$feature'..."
    Push-Location $cratePath
    try {
        cargo build --features $feature --profile $profile
    } finally {
        Pop-Location
    }
}

Write-Host "All Rust extensions built."
