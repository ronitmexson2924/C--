#!/bin/bash
# Install macOS file association and custom icon for .cmm files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ASSETS_DIR="${REPO_ROOT}/assets"
APP_DIR="${HOME}/Applications/C--.app"

echo "==> Creating macOS Application Bundle at ${APP_DIR}..."
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# Copy ICNS icon
cp "${ASSETS_DIR}/cmm.icns" "${APP_DIR}/Contents/Resources/cmm.icns"

# Create minimal launcher executable
cat << 'EOF' > "${APP_DIR}/Contents/MacOS/C--"
#!/bin/bash
if [ -n "$1" ]; then
    # Open in default text editor or run via cmm
    open -t "$1"
fi
EOF
chmod +x "${APP_DIR}/Contents/MacOS/C--"

# Create Info.plist with Document Type and UTI declarations
cat << EOF > "${APP_DIR}/Contents/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>org.c-minus-minus.app</string>
    <key>CFBundleName</key>
    <string>C--</string>
    <key>CFBundleDisplayName</key>
    <string>C--</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>CFBundleIconFile</key>
    <string>cmm.icns</string>
    <key>CFBundleExecutable</key>
    <string>C--</string>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeName</key>
            <string>C-- Source File</string>
            <key>CFBundleTypeRole</key>
            <string>Editor</string>
            <key>CFBundleTypeIconFile</key>
            <string>cmm.icns</string>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>cmm</string>
            </array>
            <key>LSHandlerRank</key>
            <string>Owner</string>
            <key>LSItemContentTypes</key>
            <array>
                <string>org.c-minus-minus.cmm</string>
            </array>
        </dict>
    </array>
    <key>UTExportedTypeDeclarations</key>
    <array>
        <dict>
            <key>UTTypeIdentifier</key>
            <string>org.c-minus-minus.cmm</string>
            <key>UTTypeDescription</key>
            <string>C-- Source File</string>
            <key>UTTypeConformsTo</key>
            <array>
                <string>public.source-code</string>
                <string>public.plain-text</string>
            </array>
            <key>UTTypeIconFile</key>
            <string>cmm.icns</string>
            <key>UTTypeTagSpecification</key>
            <dict>
                <key>public.filename-extension</key>
                <array>
                    <string>cmm</string>
                </array>
            </dict>
        </dict>
    </array>
</dict>
</plist>
EOF

echo "==> Registering with macOS LaunchServices..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f -R -trusted "${APP_DIR}"

echo "==> Stamping icons on all .cmm files in workspace..."
python3 "${SCRIPT_DIR}/set_cmm_icon.py" "${REPO_ROOT}"

echo "==> Done! macOS now associates .cmm files with the C-- 3D logo."
