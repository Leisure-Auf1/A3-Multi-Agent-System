# =============================================================================
# A3-Agent v1.0.0 — Windows Release Asset Builder
# =============================================================================
# Creates the Windows distribution zip from a PyInstaller build.
#
# Prerequisites:
#   1. Run `desktop\build.bat` first (Python 3.10+, pyinstaller)
#   2. Successful build at dist\A3-Agent\A3-Agent.exe
#
# Output:
#   release\A3-Agent-v1.0.0-win64.zip
#   release\A3-Agent-v1.0.0-win64.sha256
#
# Usage (PowerShell):
#   .\scripts\build-windows-release.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$VERSION = "1.0.0"
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DIST_DIR = Join-Path $PROJECT_ROOT "dist\A3-Agent"
$RELEASE_DIR = Join-Path $PROJECT_ROOT "release"
$PACKAGE_NAME = "A3-Agent-v$VERSION-win64"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  A3-Agent v$VERSION — Windows Release Builder" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Validate build exists ──────────────────
if (-not (Test-Path (Join-Path $DIST_DIR "A3-Agent.exe"))) {
    Write-Host "❌ PyInstaller build not found: $DIST_DIR\A3-Agent.exe" -ForegroundColor Red
    Write-Host "   Run the build first: desktop\build.bat" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/5] Validating build..." -ForegroundColor Green

# Run release check
$checkScript = Join-Path $PROJECT_ROOT "scripts\release_check.py"
if (Test-Path $checkScript) {
    python $checkScript --dist $DIST_DIR
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Release validation failed — see output above" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "⚠ release_check.py not found — skipping validation" -ForegroundColor Yellow
}
Write-Host ""

# ── Prepare release directory ──────────────
Write-Host "[2/5] Preparing release directory..." -ForegroundColor Green
if (Test-Path $RELEASE_DIR) {
    Remove-Item -Recurse -Force "$RELEASE_DIR\$PACKAGE_NAME" -ErrorAction SilentlyContinue
    Remove-Item -Force "$RELEASE_DIR\$PACKAGE_NAME.zip" -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path "$RELEASE_DIR\$PACKAGE_NAME" | Out-Null

# ── Copy build output ──────────────────────
Write-Host "[3/5] Copying build output..." -ForegroundColor Green
Copy-Item -Recurse "$DIST_DIR\*" "$RELEASE_DIR\$PACKAGE_NAME\"

# ── Add documentation ──────────────────────
Write-Host "[4/5] Adding documentation files..." -ForegroundColor Green

# LICENSE
$license = Join-Path $PROJECT_ROOT "LICENSE"
if (Test-Path $license) {
    Copy-Item $license "$RELEASE_DIR\$PACKAGE_NAME\"
    Write-Host "  ✓ LICENSE"
}

# README
$readme = Join-Path $PROJECT_ROOT "README.md"
if (Test-Path $readme) {
    Copy-Item $readme "$RELEASE_DIR\$PACKAGE_NAME\README.txt"
    Write-Host "  ✓ README.txt"
}

# VERSION
"$PACKAGE_NAME" | Out-File -Encoding ASCII "$RELEASE_DIR\$PACKAGE_NAME\VERSION"
Write-Host "  ✓ VERSION"

# ── Create zip ─────────────────────────────
Write-Host "[5/5] Creating zip archive..." -ForegroundColor Green
$zipPath = "$RELEASE_DIR\$PACKAGE_NAME.zip"
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}
Compress-Archive -Path "$RELEASE_DIR\$PACKAGE_NAME" -DestinationPath $zipPath

# ── Generate SHA256 ────────────────────────
$hash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash.ToLower()
$shaPath = "$RELEASE_DIR\$PACKAGE_NAME.sha256"
"$hash  $PACKAGE_NAME.zip" | Out-File -Encoding ASCII $shaPath

Write-Host ""
Write-Host "  SHA256: $hash" -ForegroundColor Cyan

# ── Summary ────────────────────────────────
$size = (Get-Item $zipPath).Length
$sizeMB = [math]::Round($size / 1MB, 1)

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Release package created:" -ForegroundColor Green
Write-Host "    $zipPath" -ForegroundColor White
Write-Host "    $shaPath" -ForegroundColor White
Write-Host ""
Write-Host "  Size: $sizeMB MB" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To publish on GitHub:" -ForegroundColor Yellow
Write-Host "  gh release upload v$VERSION release\$PACKAGE_NAME.zip release\$PACKAGE_NAME.sha256"
