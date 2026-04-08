#!/usr/bin/env bash
# ============================================================================
# release.sh — Create a GitHub release for ha-sh-update-manager
#
# IMPORTANT: GitHub fine-grained PATs ignore "draft": false on POST.
# This script ALWAYS patches the release after creation to force non-draft.
#
# Usage:
#   export GITHUB_PAT="github_pat_..."
#   ./scripts/release.sh "vX.Y.Z: Title" "Release notes here"
#
# The version is read automatically from manifest.json.
# ============================================================================
set -euo pipefail

REPO="csmadeit/ha-sh-update-manager"
API="https://api.github.com/repos/$REPO/releases"

# ---------------------------------------------------------------------------
# 1. Resolve the GitHub PAT
# ---------------------------------------------------------------------------
if [[ -z "${GITHUB_PAT:-}" ]]; then
  echo "ERROR: GITHUB_PAT environment variable is not set."
  echo "Export it before running:  export GITHUB_PAT=github_pat_..."
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Read version from manifest.json
# ---------------------------------------------------------------------------
MANIFEST="custom_components/sh_update_manager/manifest.json"
if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: $MANIFEST not found. Run this script from the repo root."
  exit 1
fi

VERSION=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['version'])")
TAG="v$VERSION"
echo "Version from manifest.json: $VERSION  (tag: $TAG)"

# ---------------------------------------------------------------------------
# 3. Accept release title & body (or use defaults)
# ---------------------------------------------------------------------------
TITLE="${1:-$TAG}"
BODY="${2:-Release $TAG}"

# ---------------------------------------------------------------------------
# 4. Create the release (will likely be draft despite draft:false)
# ---------------------------------------------------------------------------
echo ""
echo "Creating GitHub release $TAG ..."
CREATE_RESPONSE=$(curl -s -X POST "$API" \
  -H "Authorization: Bearer $GITHUB_PAT" \
  -H "Accept: application/vnd.github+json" \
  -d "$(python3 -c "
import json, sys
print(json.dumps({
    'tag_name': '$TAG',
    'target_commitish': 'release',
    'name': '$TITLE',
    'body': '''$BODY''',
    'draft': False,
    'prerelease': False
}))
")")

RELEASE_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true)

if [[ -z "$RELEASE_ID" ]]; then
  echo "ERROR: Failed to create release. Response:"
  echo "$CREATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CREATE_RESPONSE"
  exit 1
fi

echo "Release created (id=$RELEASE_ID). Now forcing non-draft via PATCH..."

# ---------------------------------------------------------------------------
# 5. PATCH to force draft=false, then VERIFY with a separate GET.
#    Fine-grained PATs: PATCH response may claim draft=False but the
#    release can revert to draft due to GitHub eventual consistency.
#    We do an initial PATCH+verify loop, then a DELAYED re-check after
#    30 seconds to catch any late reverts.
# ---------------------------------------------------------------------------
_patch_and_verify() {
  local rid="$1" label="$2" max="$3"
  for attempt in $(seq 1 "$max"); do
    echo "  $label attempt $attempt/$max: PATCH draft=false ..."
    curl -s -X PATCH "$API/$rid" \
      -H "Authorization: Bearer $GITHUB_PAT" \
      -H "Accept: application/vnd.github+json" \
      -d '{"draft": false}' > /dev/null

    sleep 5

    DRAFT_STATUS=$(curl -s "$API/$rid" \
      -H "Authorization: Bearer $GITHUB_PAT" \
      -H "Accept: application/vnd.github+json" \
      | python3 -c "import sys,json; print(json.load(sys.stdin).get('draft','unknown'))" 2>/dev/null || true)

    echo "  GET verification: draft=$DRAFT_STATUS"

    if [[ "$DRAFT_STATUS" == "False" ]]; then
      return 0
    fi
  done
  return 1
}

echo ""
echo "--- Round 1: initial PATCH+verify ---"
if ! _patch_and_verify "$RELEASE_ID" "Round-1" 5; then
  echo "ERROR: Release $TAG is STILL draft after 5 attempts!"
  echo "Manually un-draft at: https://github.com/$REPO/releases/edit/$TAG"
  exit 1
fi
echo "Release $TAG draft=False after round 1."
echo "URL: https://github.com/$REPO/releases/tag/$TAG"

echo ""
echo "--- Round 2: delayed re-check (30 s) to catch eventual-consistency reverts ---"
sleep 30

DRAFT_STATUS=$(curl -s "$API/$RELEASE_ID" \
  -H "Authorization: Bearer $GITHUB_PAT" \
  -H "Accept: application/vnd.github+json" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('draft','unknown'))" 2>/dev/null || true)

echo "  Delayed GET: draft=$DRAFT_STATUS"

if [[ "$DRAFT_STATUS" != "False" ]]; then
  echo "  Draft reverted! Re-patching..."
  if ! _patch_and_verify "$RELEASE_ID" "Round-2" 5; then
    echo "ERROR: Release $TAG keeps reverting to draft!"
    echo "Manually un-draft at: https://github.com/$REPO/releases/edit/$TAG"
    exit 1
  fi
  echo "  Waiting 30 s for final confirmation..."
  sleep 30
  DRAFT_STATUS=$(curl -s "$API/$RELEASE_ID" \
    -H "Authorization: Bearer $GITHUB_PAT" \
    -H "Accept: application/vnd.github+json" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('draft','unknown'))" 2>/dev/null || true)
  echo "  Final GET: draft=$DRAFT_STATUS"
  if [[ "$DRAFT_STATUS" != "False" ]]; then
    echo "ERROR: Release $TAG STILL reverted to draft after all attempts!"
    echo "Manually un-draft at: https://github.com/$REPO/releases/edit/$TAG"
    exit 1
  fi
fi

echo "Release $TAG confirmed non-draft (passed delayed verification)."

# ---------------------------------------------------------------------------
# 6. Final verification — re-read from API using release ID (not tag)
# ---------------------------------------------------------------------------
echo ""
echo "Final verification (using release ID $RELEASE_ID)..."
VERIFY=$(curl -s "$API/$RELEASE_ID" \
  -H "Authorization: Bearer $GITHUB_PAT" \
  -H "Accept: application/vnd.github+json" | python3 -c "import sys,json; r=json.load(sys.stdin); print(f'  tag={r[\"tag_name\"]} draft={r[\"draft\"]} url={r[\"html_url\"]}')" 2>/dev/null || true)
echo "$VERIFY"
echo ""
echo "Done. HACS should see $TAG."
