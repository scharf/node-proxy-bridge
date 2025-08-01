#!/bin/bash
# deploy.sh

# Check if version provided
if [ -z "$1" ]; then
    echo "Error: Version not provided"
    echo "Usage: ./deploy.sh VERSION"
    echo "Example: ./deploy.sh 1.0"
    exit 1
fi

VERSION=$1

# Confirmation prompt
echo "Deploy version ${VERSION}?"
echo "This will:"
echo "  - Create git tag v${VERSION}"
echo "  - Build Docker image ${VERSION} and latest"
echo "  - Push Docker image to Docker Hub"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 1
fi

# Deploy
echo "Creating git tag..."
git tag "v${VERSION}"
git push origin "v${VERSION}"

echo "Building Docker image..."
docker build -t scharf/node-proxy-bridge:${VERSION} .
docker tag scharf/node-proxy-bridge:${VERSION} scharf/node-proxy-bridge:latest

echo "Pushing to Docker Hub..."
docker push scharf/node-proxy-bridge:${VERSION}
docker push scharf/node-proxy-bridge:latest

echo "Done: version ${VERSION} deployed"
