#!/bin/bash

# Build DEB package for MarkAPI
# Usage: ./build-deb.sh [version]

VERSION=${1:-1.0.0}
PACKAGE_NAME="markapi"
ARCH="amd64"
MAINTAINER="SciELO Team <dev@scielo.org>"

echo "Building DEB package: ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

# Create package structure
PKG_DIR="dist/${PACKAGE_NAME}_${VERSION}_${ARCH}"
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR"/{DEBIAN,usr/bin,usr/share/markapi,etc/markapi,usr/share/applications,usr/share/pixmaps}

# DEBIAN control file
cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: $PACKAGE_NAME
Version: $VERSION
Section: science
Priority: optional
Architecture: $ARCH
Depends: git
Recommends: docker.io (>= 20.0) | docker-ce | docker-ce-cli, docker-compose (>= 1.25)
Suggests: docker-buildx-plugin
Maintainer: $MAINTAINER
Description: SciELO XML Processor
 MarkAPI é uma ferramenta para validação, processamento e conversão
 de documentos XML no contexto de publicações científicas SciELO.
 .
 Funcionalidades:
  - Validação de XML contra esquemas
  - Conversão para HTML, DOCX e PDF
  - Interface web intuitiva
  - API REST para integração
 .
 Requer Docker para funcionar (pode ser docker.io, docker-ce ou Docker Desktop).
Homepage: https://github.com/scieloorg/markapi
EOF

# Post-installation script
cat > "$PKG_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Add user to docker group if exists
if id -u markapi &>/dev/null; then
    usermod -aG docker markapi 2>/dev/null || true
fi

# Add current user to docker group
if [ "$SUDO_USER" ]; then
    usermod -aG docker "$SUDO_USER" 2>/dev/null || true
fi

# Enable and start docker
systemctl enable docker 2>/dev/null || true
systemctl start docker 2>/dev/null || true

# Create application directories
mkdir -p /var/lib/markapi/{uploads,logs,backups}
chown -R root:docker /var/lib/markapi 2>/dev/null || true
chmod -R 775 /var/lib/markapi 2>/dev/null || true

echo ""
echo "MarkAPI instalado com sucesso!"
echo ""
echo "Para iniciar:"
echo "  markapi start"
echo ""
echo "Acesse: http://localhost:8000"
echo "Documentação: https://github.com/scieloorg/markapi"
echo ""

# Note about docker group
if [ "$SUDO_USER" ]; then
    echo "IMPORTANTE: Faça logout e login novamente para usar o comando 'markapi'"
    echo "Ou execute: sudo -u $SUDO_USER markapi start"
fi
EOF

# Pre-removal script
cat > "$PKG_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e

# Stop markapi if running
if command -v markapi &> /dev/null; then
    markapi stop 2>/dev/null || true
fi
EOF

# Post-removal script
cat > "$PKG_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

case "$1" in
    purge)
        # Remove application data
        rm -rf /var/lib/markapi 2>/dev/null || true

        # Remove docker volumes (optional)
        docker volume prune -f 2>/dev/null || true
        ;;
esac
EOF

# Make scripts executable
chmod 755 "$PKG_DIR/DEBIAN/postinst"
chmod 755 "$PKG_DIR/DEBIAN/prerm"
chmod 755 "$PKG_DIR/DEBIAN/postrm"

# Copy application files
cp ../universal/markapi "$PKG_DIR/usr/bin/"
chmod 755 "$PKG_DIR/usr/bin/markapi"

# Copy application data
cp -r ../universal/* "$PKG_DIR/usr/share/markapi/"
chmod 755 "$PKG_DIR/usr/share/markapi/markapi"

# Create configuration
cp ../universal/.env.example "$PKG_DIR/etc/markapi/markapi.conf"

# Create desktop file
cat > "$PKG_DIR/usr/share/applications/markapi.desktop" << EOF
[Desktop Entry]
Name=MarkAPI
Comment=SciELO XML Processor
Exec=markapi start
Icon=markapi
Terminal=false
Type=Application
Categories=Office;Science;Development;
Keywords=xml;scielo;publishing;
EOF

# Create icon (placeholder)
cat > "$PKG_DIR/usr/share/pixmaps/markapi.xpm" << 'EOF'
/* XPM */
static char * markapi_xpm[] = {
"32 32 3 1",
" 	c None",
".	c #0066CC",
"+	c #FFFFFF",
"                                ",
"    ........................    ",
"   ..........................   ",
"  ............................  ",
" ..+++++++++++++++++++++++++++.. ",
" .+                          +. ",
" .+        MarkAPI           +. ",
" .+                          +. ",
" .+     SciELO XML          +. ",
" .+     Processor           +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" .+                          +. ",
" ..+++++++++++++++++++++++++++.. ",
"  ............................  ",
"   ..........................   ",
"    ........................    ",
"                                "};
EOF

# Build package
dpkg-deb --build "$PKG_DIR"

echo "Package created: ${PKG_DIR}.deb"
echo ""
echo "To install:"
echo "  sudo dpkg -i ${PKG_DIR}.deb"
echo "  sudo apt-get install -f"
echo ""