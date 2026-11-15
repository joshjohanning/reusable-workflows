# reusable-workflows

Reusable GitHub Actions workflows and actions.

## Upgrade Agentic Workflows

The [`gh-aw-upgrade`](gh-aw-upgrade/action.yml) composite action keeps
[GitHub Agentic Workflows (gh-aw)](https://github.com/github/gh-aw) up to date in
the current repository. It:

1. Checks out the base branch with the provided token.
2. Resolves the target gh-aw version (latest stable release by default).
3. Skips if an upgrade PR is already open against the base branch.
4. Runs `gh aw upgrade` (codemods, action pins, agent and skill files, and
   recompiled lock files).
5. Updates other `github/gh-aw-actions/setup-cli` pins (SHA, version comment,
   `version:` input, and matching `--action-tag` SHAs) in non-lock workflow files.
6. Runs `gh aw compile --validate` and fails the run on errors, because
   `gh aw upgrade` only warns when a codemod or compile fails.
7. Opens a PR titled `chore: upgrade agentic workflows to gh-aw <version>` only
   when files change. It never merges, force-pushes, or closes existing PRs.

If the compile fails, no PR is opened. Check the failed run's logs and fix the
workflows by hand or with Copilot. Compiling can't catch changes in runtime
behavior, so review the gh-aw release notes before merging an upgrade PR.

Each PR uses a unique `gh-aw-upgrade/<version>-<run-id>-<attempt>` branch, so a
closed, unmerged upgrade can be proposed again without overwriting prior work.

### Token

The caller supplies the `token`: a GitHub App installation token, a PAT, or
`github.token`. It needs **Contents**, **Pull requests**, and **Workflows**
write access. `github.token` cannot push changes to `.github/workflows/` files
(which every gh-aw upgrade touches), and PRs it opens don't trigger other
workflows, so use an App token or PAT in practice.

### Usage

```yaml
name: Upgrade Agentic Workflows

on:
  schedule:
    - cron: "0 15 * * 2" # Tuesdays
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: gh-aw-upgrade
  cancel-in-progress: false

jobs:
  upgrade:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/create-github-app-token@64ab729a6294000f5aa4a4bc0b73d1f32bc45510 # v3.3.0
        id: app-token
        with:
          client-id: ${{ vars.APP_CLIENT_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}

      - uses: joshjohanning/reusable-workflows/gh-aw-upgrade@main
        with:
          token: ${{ steps.app-token.outputs.token }}
```

### Inputs

| Name | Default | Description |
| --- | --- | --- |
| `token` | (required) | Token for checkout, push, and PR creation. |
| `gh-aw-version` | `latest` | Stable gh-aw version, e.g. `v1.2.2`. |
| `approve` | `false` | Accept safe-update manifest changes. |
| `pin-actions-to-sha` | `false` | Use SHA action-mode compilation. |
| `base-branch` | default branch | Branch to upgrade and target with the PR. |
| `git-user-name` | `github-actions[bot]` | Commit author name. |
| `git-user-email` | `github-actions[bot]` noreply | Commit author email. |

`approve` passes `--approve` to `gh aw upgrade`; leave it off unless you want to
approve safe-update manifest changes. `pin-actions-to-sha` recompiles with
`--action-mode action --action-tag <setup-cli SHA>` for repositories whose lock
files and validation commands use that mode.

### Outputs

| Name | Description |
| --- | --- |
| `pull-request-url` | URL of the opened upgrade PR, if any. |

### Local checks

Run `python3 -m unittest discover -s tests -v` (requires GNU `sed` and bash 4+).
