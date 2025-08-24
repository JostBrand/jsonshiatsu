#!/usr/bin/env bash

# Release script for jsonshiatsu
# Usage: ./release.sh <version> [message]
# Example: ./release.sh v0.2.0 "Major CI improvements and test fixes"

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <version> [message]"
    echo "Example: $0 v0.2.0 'Major CI improvements'"
    exit 1
fi

VERSION=$1
MESSAGE=${2:-"Release $VERSION"}

# Validate version format
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
    echo "❌ Version must follow format: v1.2.3 or v1.2.3-alpha"
    echo "   Got: $VERSION"
    exit 1
fi

# Extract numeric version (remove 'v' prefix)
NUMERIC_VERSION=${VERSION#v}

echo "🚀 Preparing release $VERSION"

# Update version in pyproject.toml (only the package version in [tool.poetry] section)
echo "📝 Updating version in pyproject.toml to $NUMERIC_VERSION"
sed -i "/\[tool\.poetry\]/,/\[/ s/version = \"[^\"]*\"/version = \"$NUMERIC_VERSION\"/" pyproject.toml

# Run tests to make sure everything is working
echo "🧪 Running tests..."
poetry run pytest tests/ -q

# Run linting
echo "🔍 Running linting..."
poetry run ruff check jsonshiatsu tests examples
poetry run ruff format --check jsonshiatsu tests examples

# Run type checking
echo "📋 Running type checking..."
poetry run mypy jsonshiatsu

echo "✅ All checks passed!"

# Stage the version change
git add pyproject.toml

# Check if there are any other staged changes
if git diff --cached --quiet; then
    echo "⚠️  No changes staged for commit"
else
    # Commit the version update
    echo "💾 Committing version update..."
    git commit -m "Bump version to $NUMERIC_VERSION"
fi

# Create and push the tag
echo "🏷️  Creating tag $VERSION..."
git tag -a "$VERSION" -m "$MESSAGE"

echo "📤 Pushing tag to origin..."
git push origin "$VERSION"

echo ""
echo "🎉 Release $VERSION has been triggered!"
echo "   Check GitHub Actions: https://github.com/$(git config --get remote.origin.url | sed 's|.*github.com[:/]||' | sed 's|\.git||')/actions"
echo ""
echo "📦 The release will:"
echo "   ✅ Run all tests"
echo "   ✅ Build wheel and source distribution"
echo "   ✅ Create GitHub release with auto-generated notes"
echo "   ✅ Upload build artifacts"
echo "   ✅ Publish to PyPI (if PYPI_TOKEN is configured)"
echo ""
