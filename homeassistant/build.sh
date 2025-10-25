#!/usr/bin/env bash
# ==============================================================================
# Build script for FaceInsight Home Assistant Add-on
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ADDON_NAME="faceinsight"
VERSION=$(jq -r '.version' homeassistant/config.json)
ARCHITECTURES=("amd64" "aarch64")

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}FaceInsight Add-on Builder${NC}"
echo -e "${GREEN}Version: ${VERSION}${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to build for specific architecture
build_arch() {
    local arch=$1
    echo -e "${YELLOW}Building for ${arch}...${NC}"
    
    docker build \
        --build-arg BUILD_FROM="$(jq -r ".build_from.${arch}" homeassistant/build.json)" \
        --build-arg BUILD_ARCH="${arch}" \
        --build-arg BUILD_VERSION="${VERSION}" \
        -f homeassistant/Dockerfile \
        -t "local/${ADDON_NAME}:${VERSION}-${arch}" \
        .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully built ${arch}${NC}"
    else
        echo -e "${RED}✗ Failed to build ${arch}${NC}"
        exit 1
    fi
}

# Main build process
echo -e "${YELLOW}Starting build process...${NC}"
echo ""

# Build for each architecture
for arch in "${ARCHITECTURES[@]}"; do
    build_arch "$arch"
    echo ""
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Built images:"
for arch in "${ARCHITECTURES[@]}"; do
    echo "  - local/${ADDON_NAME}:${VERSION}-${arch}"
done
echo ""
echo -e "${YELLOW}To test locally:${NC}"
echo "  docker run --rm -p 6080:6080 local/${ADDON_NAME}:${VERSION}-amd64"
echo ""
echo -e "${YELLOW}To push to registry:${NC}"
echo "  ./homeassistant/publish.sh"
