#!/bin/bash
# deploy.sh

# Check if version provided
if [ -z "$1" ]; then
    echo "Error: Version not provided"
    echo "Usage: ./deploy.sh VERSION"
    echo "Example: ./deploy.sh 1.0.1"
    exit 1
fi

VERSION=$1

# Confirmation prompt
echo "Deploy version ${VERSION}?"
echo "This will:"
echo "  - Create git tag v${VERSION}"
echo "  - Build multi-platform Docker images (amd64 & arm64)"
echo "  - Push Docker images to Docker Hub"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 1
fi

# Check if docker buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    echo "Error: docker buildx is required for multi-platform builds"
    echo "Please update Docker Desktop or install buildx"
    exit 1
fi

# Create git tag
echo "Creating git tag..."
if ! git tag "v${VERSION}"; then
    echo "Error: Failed to create git tag. Does v${VERSION} already exist?"
    exit 1
fi

if ! git push origin "v${VERSION}"; then
    echo "Error: Failed to push git tag"
    exit 1
fi

# Setup buildx if needed
echo "Setting up Docker buildx..."
docker buildx create --name mybuilder --use 2>/dev/null || docker buildx use mybuilder

# Build and push multi-platform image
echo "Building multi-platform Docker images..."
if ! docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t scharf/node-proxy-bridge:${VERSION} \
    -t scharf/node-proxy-bridge:latest \
    --push \
    .; then
    echo "Error: Docker build failed"
    exit 1
fi

echo "✓ Successfully deployed version ${VERSION}"
echo ""
echo "Images available at:"
echo "  - scharf/node-proxy-bridge:${VERSION}"
echo "  - scharf/node-proxy-bridge:latest"
echo ""
echo "Platforms: linux/amd64, linux/arm64"
