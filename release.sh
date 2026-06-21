#!/bin/bash
# Release script for tempmail-cli
# Usage: ./release.sh <version>
# Example: ./release.sh 0.2.0

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 0.2.0"
    exit 1
fi

VERSION=$1
TAG="v$VERSION"

echo "=== Release $VERSION ==="

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Error: Tag $TAG already exists"
    exit 1
fi

# Update version in __init__.py
echo "Updating version to $VERSION in src/tempmail_cli/__init__.py"
sed -i '' "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/tempmail_cli/__init__.py

# Update version in pyproject.toml
echo "Updating version to $VERSION in pyproject.toml"
sed -i '' "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Update CHANGELOG.md
echo "Updating CHANGELOG.md"
DATE=$(date +%Y-%m-%d)
sed -i '' "/## \[Unreleased\]/a\\
\\
## [$VERSION] - $DATE" CHANGELOG.md

# Run checks
echo "Running lint check..."
ruff check src/ tests/

echo "Running type check..."
mypy src/tempmail_cli/

echo "Running tests..."
pytest --cov=tempmail_cli -q

# Commit changes
echo "Committing changes..."
git add src/tempmail_cli/__init__.py pyproject.toml CHANGELOG.md
git commit -m "chore: release v$VERSION"

# Create tag
echo "Creating tag $TAG..."
git tag -a "$TAG" -m "Release $VERSION"

echo ""
echo "=== Release $VERSION prepared ==="
echo ""
echo "Next steps:"
echo "  1. Push changes: git push origin main"
echo "  2. Push tags: git push origin $TAG"
echo ""
echo "GitHub Actions will automatically:"
echo "  - Run CI tests"
echo "  - Build the package"
echo "  - Create GitHub Release"
echo "  - Publish to PyPI"
