#!/bin/bash

# Get version from git tags or generate one
# This script provides consistent version tagging for CI/CD

set -e

# Get the latest git tag that matches semantic versioning
LATEST_TAG=$(git describe --tags --match "v*.*.*" --abbrev=0 2>/dev/null || echo "v0.0.0")

# Get current commit hash (short)
SHORT_SHA=$(git rev-parse --short HEAD)

# Get current branch
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

# If we're on main branch and there are commits since last tag
if [[ "$BRANCH" == "main" ]]; then
    # Check if current commit is already tagged
    CURRENT_TAG=$(git describe --exact-match --tags HEAD 2>/dev/null || echo "")

    if [[ -n "$CURRENT_TAG" ]]; then
        # Current commit is tagged, use the tag
        echo "${CURRENT_TAG#v}"
    else
        # Count commits since last tag
        COMMITS_SINCE_TAG=$(git rev-list ${LATEST_TAG}..HEAD --count)

        if [[ $COMMITS_SINCE_TAG -gt 0 ]]; then
            # Parse version components
            VERSION=${LATEST_TAG#v}
            IFS='.' read -r -a VERSION_PARTS <<< "$VERSION"
            MAJOR=${VERSION_PARTS[0]}
            MINOR=${VERSION_PARTS[1]}
            PATCH=${VERSION_PARTS[2]}

            # Auto-increment patch version
            PATCH=$((PATCH + 1))
            NEW_VERSION="$MAJOR.$MINOR.$PATCH"
            echo "$NEW_VERSION"
        else
            # No commits since tag, use current tag
            echo "${LATEST_TAG#v}"
        fi
    fi
else
    # Non-main branch, use latest tag with branch and SHA
    VERSION=${LATEST_TAG#v}
    echo "$VERSION-$BRANCH-$SHORT_SHA"
fi
