# forge-workflow

Marketplace of **recipes** (one-form Job templates) and **pipelines**
(workflow YAMLs) for [Forge](https://github.com/aiwatching/forge).

## Layout

```
forge-workflow/
  registry.json              ← clients sync this to get the catalog
  recipes/
    <name>/
      recipe.yaml            ← the actual recipe
      info.json              ← richer metadata (rating, tags)
  pipelines/
    <name>/
      pipeline.yaml          ← workflow yaml (= the file in ~/.forge/data/flows/)
      info.json
```

## Bumping a recipe or pipeline

`registry.json` must stay in sync with every `info.json`. The helper
does the rebuild; CI rejects PRs with drift.

```bash
python3 tools/build_registry.py            # rebuild from info.json files
python3 tools/build_registry.py --check    # exits non-zero on drift
```

The script also warns when `pipeline.yaml`'s `version:` doesn't match
its sibling `info.json` (yaml = what Forge runs at dispatch time,
info.json = what the marketplace lists — they need to agree or users
install the "v0.6.0" they see but actually run "v0.5.0").

## Concepts

- **Recipe** = a one-form template that turns 2–4 user-filled fields
  into a fully wired **Job** row. Recipes pick a connector tool, set
  `items_path` / `dedup_field`, and bind to a pipeline workflow. Users
  see a focused 4-field form instead of a 12-field one.

- **Pipeline** = a multi-node workflow YAML executed by Forge's
  pipeline engine. Recipes typically dispatch into a pipeline that does
  the real work (e.g. checkout → diff → Claude fix → push).

## How clients use this repo

A Forge instance has `workflowRepoUrl` pointing at the raw-content URL of
this repo's main branch (default in `lib/settings.ts`). On Sync:

1. Fetch `registry.json` → cache to `<dataDir>/workflow-cache.json`
2. UI shows registry items in the Recipe picker / Pipelines view
3. User clicks Install on an item → Forge fetches the per-item yaml
   from `<repo>/<recipes|pipelines>/<name>/<recipe|pipeline>.yaml`
   and writes it to `<dataDir>/recipes/` or `<dataDir>/flows/`.

## Adding a recipe

1. Create `recipes/<your-name>/`
2. Drop `recipe.yaml` and `info.json` inside
3. Append a summary entry to the `recipes` array in `registry.json`
4. PR.

## Adding a pipeline

1. Create `pipelines/<your-name>/`
2. Drop `pipeline.yaml` (your Forge workflow yaml) and `info.json`
3. Append summary to `pipelines` in `registry.json`
4. PR.

## Current contents

(Recipes have been removed along with the deprecated Jobs module.
Use Schedules + Fire-button pipelines instead.)

| Pipeline | What it does |
|---|---|
| `fortinet-mantis-bug-fix` | Single Fortinet Mantis bug → worktree → Claude fix → MR → notify |
| `fortinet-mantis-bug-fix-batch` | N bug ids per Fire (for_each loop, no child dispatch) |
| `fortinet-mr-review` | Single Fortinet GitLab MR — read all comments, triage, push fixup, reply, notify |
| `fortinet-mr-review-batch` | N MR iids OR author/labels filter (for_each.before resolves at run time) |
| `fortinet-mr-pre-review` | Pre-review pass on a Fortinet MR — analyze + post markdown comment |
| `issue-fix-and-review` | GitHub issue scanner |
| `multi-agent-collaboration` | Multi-agent conversation demo |
| `review-mr` | GitHub PR auto-review |
