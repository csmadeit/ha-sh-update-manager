# Releasing — SH Auto Update Manager

by **Smarter Homes LLC** — [smarter.homes](https://smarter.homes)

## Release Process

1. Update `version` in `custom_components/sh_update_manager/manifest.json`
2. Update version history in `README.md`, `SPECIFICATION.md`, and this file
3. Commit: `git commit -am "v1.x.x: description"`
4. Tag: `git tag v1.x.x`
5. Push: `git push origin main --tags`
6. Run: `./scripts/release.sh v1.x.x`

## Version History

### v1.0.0 — 2026-04-08
- Initial release
- Queue manager with sequential update installation
- Config flow + Options flow with full settings UI
- 7 sensor entities (queue status, pending, current, last success/failure, counts)
- 4 button entities (update all, refresh, stop, skip)
- 2 switch entities (auto-update, pause queue)
- 8 service actions for queue control and automation
- Persistent queue state across HA restarts
- Maintenance window scheduling
- Integration / area / label / entity filtering
- Mains-powered-only mode for Z-Wave firmware safety
- Category filter (all updates vs firmware-only)
