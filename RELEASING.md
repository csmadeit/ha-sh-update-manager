# Release Process

## Overview

This integration is hosted on **GitHub** for HACS distribution.

- **GitHub:** https://github.com/csmadeit/ha-sh-update-manager
- **HACS default branch:** `release`

## CRITICAL: Version Alignment Rules

**The `version` field in `manifest.json` MUST always match the GitHub release tag.**

HACS compares the installed version (from `manifest.json`) against the latest GitHub release tag.
If `manifest.json` has a higher version than the release tag, HACS will never show an update.

**Before every release:**
1. Update `version` in `custom_components/sh_update_manager/manifest.json` to the new version
2. Commit and push that change to the `release` branch
3. Create a git tag with the SAME version (prefixed with `v`)
4. Push the tag
5. Create a GitHub release using `./scripts/release.sh`

**Example:** To release version `1.2.0`:
- `manifest.json` must say `"version": "1.2.0"`
- Git tag must be `v1.2.0`
- GitHub release must be tagged `v1.2.0`

**Never** create a GitHub release tag that is lower than the `manifest.json` version.

## How to Release a New Version

### 1. Bump the version

Edit `custom_components/sh_update_manager/manifest.json` and update the `version` field.

### 2. Update version history

Update the version history in `README.md`, `SPECIFICATION.md`, and this file.

### 3. Commit and push

```bash
git add -A
git commit -m "vX.Y.Z: Brief description"
git push origin release
```

### 4. Create a version tag

```bash
# IMPORTANT: Version in tag MUST match version in manifest.json
# Verify first:
grep '"version"' custom_components/sh_update_manager/manifest.json

# Create annotated tag (must match manifest.json version)
git tag -a vX.Y.Z -m "vX.Y.Z: Brief description of changes"

# Push tag
git push origin vX.Y.Z
```

### 5. Create GitHub Release

**ALWAYS use the release script** to avoid the draft release bug:

```bash
export GITHUB_PAT="github_pat_..."
./scripts/release.sh "vX.Y.Z: Title" "Release notes here"
```

The script reads the version from `manifest.json`, creates the release, and
automatically PATCHes it to non-draft with verification.

> **WARNING — DRAFT RELEASE BUG:** GitHub fine-grained PATs silently ignore
> `"draft": false` on `POST /releases`. The release is ALWAYS created as a
> draft. The ONLY fix is to follow the POST with a `PATCH` that sets
> `{"draft": false}`. The `scripts/release.sh` script handles this
> automatically. **NEVER create releases manually via the API without the
> PATCH step — HACS cannot see draft releases.**

### 6. HACS picks up the release

HACS automatically detects new GitHub releases. Users will see the update in HACS.

## Version History

| Version | Date | Description |
|---------|------|-------------|
| v1.0.0 | 2026-04-08 | Initial release — sequential queue, global settings |
| v1.1.0 | 2026-04-08 | Per-group execution modes, manual approval, Z-Wave/HA safety overrides |

## HACS Custom Repository Setup (for users)

1. Open HACS in Home Assistant
2. Go to **Integrations** > three-dot menu > **Custom repositories**
3. Add URL: `https://github.com/csmadeit/ha-sh-update-manager`
4. Category: **Integration**
5. Click **Add**
6. Install **Smarter.Homes Update Manager**
7. Restart Home Assistant
