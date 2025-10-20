#!/bin/bash

# Build AppImage for MarkAPI
# Usage: ./build-appimage.sh [version]

VERSION=${1:-1.0.0}
APP_NAME="MarkAPI"

echo "Building AppImage: ${APP_NAME}-${VERSION}.AppImage"

# Create AppDir structure
APPDIR="${APP_NAME}.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR"/{usr/bin,usr/share/applications,usr/share/icons/hicolor/256x256/apps}

# Create AppRun script
cat > "$APPDIR/AppRun" << 'APPRUN_EOF'
#!/bin/bash

# MarkAPI AppImage Launcher

APPDIR="$(dirname "$(readlink -f "$0")")"
export PATH="$APPDIR/usr/bin:$PATH"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    if command -v zenity &> /dev/null; then
        zenity --error --title="MarkAPI" --text="Docker não está instalado!\n\nInstale Docker para usar o MarkAPI:\n\nUbuntu/Debian: sudo apt install docker.io\nFedora: sudo dnf install docker\nArch: sudo pacman -S docker"
    else
        echo "ERRO: Docker não está instalado!"
        echo "Instale Docker para usar o MarkAPI"
    fi
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    if command -v zenity &> /dev/null; then
        zenity --error --title="MarkAPI" --text="Docker não está rodando!\n\nInicie Docker:\nsudo systemctl start docker\n\nOu adicione seu usuário ao grupo docker:\nsudo usermod -aG docker $USER"
    else
        echo "ERRO: Docker não está rodando!"
        echo "Inicie: sudo systemctl start docker"
    fi
    exit 1
fi

# Create working directory
WORKDIR="$HOME/.markapi"
mkdir -p "$WORKDIR"

# Copy application files if not exists
if [ ! -f "$WORKDIR/markapi" ]; then
    cp -r "$APPDIR/usr/share/markapi"/* "$WORKDIR/"
    chmod +x "$WORKDIR/markapi"
fi

# Change to working directory
cd "$WORKDIR"

# Check arguments
case "$1" in
    ""|"start")
        ./markapi start
        ;;
    *)
        ./markapi "$@"
        ;;
esac
APPRUN_EOF

chmod +x "$APPDIR/AppRun"

# Copy application files
cp -r ../universal/* "$APPDIR/usr/share/markapi/"
cp ../universal/markapi "$APPDIR/usr/bin/"
chmod +x "$APPDIR/usr/bin/markapi"

# Create desktop file
cat > "$APPDIR/markapi.desktop" << EOF
[Desktop Entry]
Name=MarkAPI
Comment=SciELO XML Processor
Exec=AppRun
Icon=markapi
Type=Application
Categories=Office;Science;Development;
Keywords=xml;scielo;publishing;
X-AppImage-Version=$VERSION
