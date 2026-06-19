# langchain-prolog 1.0.2

Tooling-only maintenance release. No changes to `PrologConfig`, `PrologRunnable`, or `PrologTool` APIs.

## Internal

### Makefile / run.sh — extra flags now flow through all release targets

All `make release-*` and `rollback` targets now accept additional arguments via `ARGS ?=`:

```bash
make release-micro ARGS="--no-interactive"
```

The same flags are forwarded when calling `run.sh` functions directly (`"$@"` passthrough).

### release.yml — more reliable ReadTheDocs update

The ReadTheDocs CI step now:

- Syncs RTD versions before activating the new tag (so newly-created version slugs are visible)
- Triggers explicit builds for both the tagged version and `latest`
- Uses an HTTP `2xx` regex check instead of an exact `204` match (more permissive and correct)
- Reports success/warning conditionally in the Release Summary via `id: update-rtd`

### README.md

Removed a stale hardcoded version badge that was left over from an earlier release.

## Full changelog

See [`CHANGELOG.md`](CHANGELOG.md) for the complete list of changes.
