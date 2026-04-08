# GitHub Release Gotchas for HACS Integrations

This document captures hard-won lessons from releasing HACS custom integrations
via GitHub. These apply to ALL SH (Smarter Homes) HACS repos.

---

## 1. manifest.json Version MUST Match Release Tag

**Rule:** The `version` field in `manifest.json` must ALWAYS match the GitHub
release tag (without the `v` prefix).

| manifest.json | Git tag | GitHub release | HACS sees update? |
|---------------|---------|----------------|-------------------|
| `"1.1.0"` | `v1.1.0` | `v1.1.0` | YES |
| `"1.0.0"` | `v1.1.0` | `v1.1.0` | NO — version mismatch |
| `"1.2.0"` | `v1.1.0` | `v1.1.0` | NO — manifest higher than release |

**Why:** HACS compares the installed version (from `manifest.json` in the repo's
default branch) against the latest GitHub release tag. If `manifest.json` has a
*higher* version than the latest release tag, HACS will **never** show an update.

**Fix:** Always bump `manifest.json` version BEFORE creating the tag and release.

---

## 2. Fine-Grained PATs Create Draft Releases (HACS Can't See Them)

**Bug:** GitHub fine-grained Personal Access Tokens silently ignore
`"draft": false` on `POST /repos/{owner}/{repo}/releases`. The release is
ALWAYS created as a **draft**, even though the API response may say otherwise.

**Impact:** HACS cannot see draft releases. Users will never get the update.

**Fix:** After creating a release via POST, immediately PATCH it:
```bash
curl -X PATCH "https://api.github.com/repos/OWNER/REPO/releases/{release_id}" \
  -H "Authorization: Bearer $GITHUB_PAT" \
  -d '{"draft": false}'
```

Then verify with a separate GET request (the PATCH response itself can lie).

**Best practice:** ALWAYS use `./scripts/release.sh` which handles this
automatically with multiple PATCH+verify rounds and a 30-second delayed
re-check for eventual consistency.

---

## 3. NEVER Move Git Tags After Creating a Release

**Bug:** If you delete and recreate a git tag after a GitHub release was created
pointing to the old tag, the release becomes **orphaned**:

- The release reverts to **draft** status
- The release-by-tag API lookup (`/releases/tags/vX.Y.Z`) returns **404**
- HACS cannot find or see the release

**What happened (v1.1.0 incident):**
1. Created tag `v1.1.0` → commit `bb73d34`
2. Created GitHub release `v1.1.0` → worked, non-draft
3. Made a follow-up commit → `91cae92`
4. Deleted and recreated tag `v1.1.0` → now points to `91cae92`
5. GitHub release became orphaned → reverted to draft, tag lookup returned 404
6. HACS could not see v1.1.0

**Fix:** If you need to move a tag after a release exists:
1. Delete the GitHub release first (via API or web UI)
2. Delete and recreate the tag
3. Create a brand new release using `./scripts/release.sh`

**Better practice:** NEVER move tags. If you need to include a post-release
fix, create a new patch version (e.g., `v1.1.1`).

---

## 4. HACS Refresh Timing

After creating/fixing a release, HACS may not show the update immediately.

**Options to force refresh:**
- HACS sidebar → three-dot menu → "Reload" or "Check for updates"
- Restart Home Assistant
- Wait for the next automatic HACS scan (~6 hours by default)

---

## 5. Release Checklist (Do This Every Time)

```
[ ] 1. Update `version` in manifest.json
[ ] 2. Update version history in README.md, SPECIFICATION.md, RELEASING.md
[ ] 3. Commit: git commit -am "vX.Y.Z: description"
[ ] 4. Tag:    git tag -a vX.Y.Z -m "vX.Y.Z: description"
[ ] 5. Push:   git push origin release --tags
[ ] 6. Run:    export GITHUB_PAT=... && ./scripts/release.sh
[ ] 7. Verify: Check release is non-draft via API or GitHub web UI
[ ] 8. Test:   Confirm HACS shows the update (may need manual refresh)
```

**NEVER skip steps. NEVER create releases manually via curl without the PATCH
step. ALWAYS use `./scripts/release.sh`.**

---

## 6. Debugging a Release That HACS Can't See

If HACS doesn't show an update after creating a release:

```bash
# 1. Check release exists and is NOT draft
curl -s "https://api.github.com/repos/OWNER/REPO/releases/tags/vX.Y.Z" \
  -H "Authorization: Bearer $GITHUB_PAT" | python3 -c "
import sys,json; r=json.load(sys.stdin)
print(f'draft={r.get(\"draft\")}  tag={r.get(\"tag_name\")}  published={r.get(\"published_at\")}')"

# 2. If "Not Found" → release is orphaned from tag (see gotcha #3)
# 3. If draft=True → PATCH to force non-draft (see gotcha #2)
# 4. Check manifest.json version matches the tag (see gotcha #1)

# 5. Check the version HACS sees (from default branch):
curl -s "https://raw.githubusercontent.com/OWNER/REPO/release/custom_components/DOMAIN/manifest.json" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])"
```

---

## Applies To

All Smarter Homes HACS integrations:
- `ha-sh-update-manager` (Smarter.Homes Update Manager)
- `ha-schneider-xw-pro` (Schneider Electric Conext XW Pro)
- Any future `ha-sh-*` repos

---

*Last updated: 2026-04-08 — after v1.1.0 orphaned-release incident*
