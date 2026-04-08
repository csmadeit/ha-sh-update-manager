#!/usr/bin/env bash
# release.sh — Create a GitHub release for ha-sh-update-manager
#
# Usage: ./scripts/release.sh v1.0.0
#
# Prerequisites:
#   - GITHUB_PAT environment variable set
#   - jq installed
#   - Tag already pushed: git tag v1.0.0 && git push origin v1.0.0

set -euo pipefail

REPO="csmadeit/ha-sh-update-manager"
TAG="${1:?Usage: release.sh <tag>}"

echo "Creating release ${TAG} for ${REPO}..."

# Create the release
RESPONSE=$(curl -s -X POST \
  -H "Authorization: token ${GITHUB_PAT}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/releases" \
  -d "{
    \"tag_name\": \"${TAG}\",
    \"name\": \"${TAG}\",
    \"body\": \"Release ${TAG}\n\nSee RELEASING.md for version history.\",
    \"draft\": false,
    \"prerelease\": false
  }")

RELEASE_ID=$(echo "$RESPONSE" | jq -r '.id')
HTML_URL=$(echo "$RESPONSE" | jq -r '.html_url')

if [ "$RELEASE_ID" = "null" ] || [ -z "$RELEASE_ID" ]; then
  echo "ERROR: Failed to create release"
  echo "$RESPONSE" | jq .
  exit 1
fi

echo "Release created: ${HTML_URL}"
echo "Release ID: ${RELEASE_ID}"

# Verify it's not draft (fine-grained PATs can revert to draft)
echo "Verifying release is published..."
sleep 5

CHECK=$(curl -s \
  -H "Authorization: token ${GITHUB_PAT}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/releases/${RELEASE_ID}")

IS_DRAFT=$(echo "$CHECK" | jq -r '.draft')

if [ "$IS_DRAFT" = "true" ]; then
  echo "WARNING: Release reverted to draft, re-publishing..."
  curl -s -X PATCH \
    -H "Authorization: token ${GITHUB_PAT}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${REPO}/releases/${RELEASE_ID}" \
    -d '{"draft": false}' > /dev/null

  # 30s delayed re-check
  echo "Waiting 30s for eventual consistency..."
  sleep 30

  RECHECK=$(curl -s \
    -H "Authorization: token ${GITHUB_PAT}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${REPO}/releases/${RELEASE_ID}")

  IS_DRAFT=$(echo "$RECHECK" | jq -r '.draft')
  if [ "$IS_DRAFT" = "true" ]; then
    echo "ERROR: Release is still draft after retry. Check PAT permissions."
    exit 1
  fi
fi

echo "Release ${TAG} published successfully: ${HTML_URL}"
