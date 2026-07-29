# Releasing

Every package in `packages/` publishes to PyPI from this repository, triggered by a
package-prefixed tag. Each package keeps its own version and its own PyPI identity —
the monorepo does not release them together, and there is no stack-wide version.

## Cutting a release

1. Bump `version` in `packages/<package>/pyproject.toml`.
2. Update `packages/<package>/CHANGELOG.md` if the package keeps one.
3. If the package is an MCP server (it has a `server.json`), update the version there
   too — both the top-level `version` and every `packages[].version`. The workflow
   checks this and fails the release if they disagree.
4. Commit the bump on a branch, open a PR, merge it.
5. Tag the merge commit on `main` and push:

   ```bash
   git tag sql-steward-v0.4.1
   git push origin sql-steward-v0.4.1
   ```

The tag prefix is the directory name under `packages/`, so `sql-sop-mcp-v0.1.3` releases
`packages/sql-sop-mcp`. The version after `-v` must match `pyproject.toml`; the workflow
refuses the release otherwise, because the alternative is shipping one version's artifact
under another version's tag.

Keep the bump and the tag on the same commit. Splitting them is how a tag ends up
describing a version the tree does not contain.

### What the workflow does

`release-<package>.yml` is a thin caller; the work lives in `_publish.yml`:

1. **version** — tag and `pyproject.toml` must agree, or nothing runs.
2. **pypi** — builds sdist and wheel from `packages/<package>/` and publishes via
   trusted publishing. `skip-existing` is on, so re-running a partly-succeeded release
   is a no-op rather than a failure.
3. **mcp-registry** — only if the package has a `server.json`. Verifies its version
   matches, then publishes to the official MCP Registry using GitHub OIDC.
4. **github-release** — creates the release and attaches the artifacts.

Packages build standalone. The `[tool.uv.sources]` workspace redirects live in the root
`pyproject.toml`, so a published wheel's requirements always resolve to PyPI, never to a
local path.

## PyPI trusted publishing

No API tokens exist anywhere. Each package authenticates to PyPI by proving, over OIDC,
that the upload came from a specific workflow file in this repository. That binding is
configured on PyPI, not here:

| Field | Value |
|---|---|
| Owner | `Pawansingh3889` |
| Repository | `governed-agent-stack` |
| Workflow | `release-<package>.yml` |
| Environment | `pypi` |

Set at https://pypi.org → the project → *Publishing*.

**These entries still name the archived standalone repositories.** Until each is
re-pointed at `governed-agent-stack`, the publish step fails with `invalid-publisher` —
the same failure the `sql-guard` → `sql-sop` rename caused. Packages needing a
re-point: `sql-steward`, `sql-sop`, `pii-veil`, `query-warden`, `thread-recall`,
`sql-explorer-mcp`, `sql-sop-mcp`. `agent-blackbox` has never been published and needs a
*pending* publisher created instead.

`drift-gate` and `schema-scout` are not on PyPI and have no release workflow yet. Add
one from any existing `release-<package>.yml` when they are ready.

## Notes

**`sql-sop` no longer uses release-please.** It previously managed its own version and
changelog from conventional commits, opening a release PR per bump. Ten packages under
one release-please manifest was a second mechanism to get wrong, so it now follows the
same tag convention as everything else — at the cost of the automated changelog. Write
`CHANGELOG.md` by hand.

**Do not switch these tags to bot-created ones.** GitHub does not start workflows from
events made with `GITHUB_TOKEN`. That is exactly how sql-sop v0.9.0 sat tagged and
unpublished for six weeks. A tag pushed by a person fires the event reliably.
