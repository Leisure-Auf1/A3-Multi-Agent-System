#!/bin/bash
# =============================================================================
# A3-Agent v1.0.0 — Release Builder
# =============================================================================
# Creates release packages for distribution.
#
# Output:
#   release/A3-Agent-v1.0.0-linux-x64.tar.gz
#   release/A3-Agent-v1.0.0-linux-x64.sha256
#
# Prerequisites:
#   PyInstaller build must exist at dist/A3-Agent/
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="${A3_VERSION:-1.0.0}"
DIST_DIR="$PROJECT_ROOT/dist/A3-Agent"
RELEASE_DIR="$PROJECT_ROOT/release"

# ── Validate build exists ──────────────────
if [ ! -f "$DIST_DIR/A3-Agent" ]; then
    echo "❌ PyInstaller build not found: $DIST_DIR/A3-Agent"
    echo "   Run the build first: pyinstaller ... desktop/launcher.py"
    exit 1
fi

echo "============================================"
echo "  A3-Agent v$VERSION — Release Builder"
echo "============================================"
echo ""

# ── Clean + create release dir ─────────────
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# ── Validate build ─────────────────────────
echo "[1/3] Validating build..."
python "$SCRIPT_DIR/release_check.py" --dist "$DIST_DIR"
echo ""

# ── Linux package ──────────────────────────
echo "[2/3] Creating Linux package..."
PACKAGE_NAME="A3-Agent-v$VERSION-linux-x64"
mkdir -p "$RELEASE_DIR/$PACKAGE_NAME"

# Copy build output
cp -r "$DIST_DIR"/* "$RELEASE_DIR/$PACKAGE_NAME/"

# Add documentation
cp "$PROJECT_ROOT/LICENSE" "$RELEASE_DIR/$PACKAGE_NAME/" 2>/dev/null || true
cp "$PROJECT_ROOT/README.md" "$RELEASE_DIR/$PACKAGE_NAME/README.txt" 2>/dev/null || true
echo "A3-Agent v$VERSION" > "$RELEASE_DIR/$PACKAGE_NAME/VERSION"

# Create tarball
cd "$RELEASE_DIR"
tar czf "$PACKAGE_NAME.tar.gz" "$PACKAGE_NAME"
echo "  Created: release/$PACKAGE_NAME.tar.gz ($(du -h "$PACKAGE_NAME.tar.gz" | cut -f1))"

# ── Checksums ──────────────────────────────
echo "[3/3] Generating checksums..."
cd "$RELEASE_DIR"
sha256sum "$PACKAGE_NAME.tar.gz" > "$PACKAGE_NAME.sha256"
cat "$PACKAGE_NAME.sha256"
echo ""

# ── Summary ────────────────────────────────
echo "============================================"
echo "  Release packages:"
echo "    $RELEASE_DIR/$PACKAGE_NAME.tar.gz"
echo "    $RELEASE_DIR/$PACKAGE_NAME.sha256"
echo "============================================"
echo ""
echo "  Size: $(du -h "$PACKAGE_NAME.tar.gz" | cut -f1)"
echo ""
echo "  To publish on GitHub:"
echo "    gh release create v$VERSION \\"
echo "      release/$PACKAGE_NAME.tar.gz \\"
echo "      release/$PACKAGE_NAME.sha256 \\"
echo "      --title 'A3-Agent v$VERSION' \\"
echo "      --notes-file CHANGELOG.md"
