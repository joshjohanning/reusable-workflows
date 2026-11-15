# reusable-workflows

Reusable GitHub Actions workflows.

## Upgrade Agentic Workflows

The [upgrade workflow](.github/workflows/gh-aw-upgrade.yml) keeps
[GitHub Agentic Workflows (gh-aw)](https://github.com/github/gh-aw) up to date in
the calling repository. It:

1. Resolves the target gh-aw version (latest stable release by default).
2. Skips if an upgrade PR is already open against the target branch.
3. Runs `gh aw upgrade` (codemods, action pins, agent and skill files, and
   recompiled lock files).
4. Updates other `github/gh-aw-actions/setup-cli` pins (SHA, version comment,
   `version:` input, and matching `--action-tag` SHAs) in non-lock workflow files.
5. Opens a PR titled `chore: upgrade agentic workflows to gh-aw <version>` only
   when files change. It never merges, force-pushes, or closes existing PRs.

Runs are serialized per repository and base branch. Each new PR uses a unique
`gh-aw-upgrade/<version>-<run-id>-<attempt>` branch, so a closed, unmerged upgrade
can be proposed again without overwriting prior work. Current compiler versions
do not skip validation-pin and action updates.

### Credentials

`GITHUB_TOKEN` cannot push changes to workflow files, so provide one of these:

- **GitHub App** (recommended): pass the `app-client-id` input and
  `app-private-key` secret. Install the App on the repository with **Contents**,
  **Pull requests**, and **Workflows** read and write permissions.
- **PAT**: pass the `token` secret, with the same permissions.

PRs opened with an App or PAT token trigger the repository's normal PR checks.
An existing App or PAT can be reused; no specially named upgrade token is needed.
For a classic PAT, use `repo` and `workflow` scopes.

### Usage

```yaml
name: Upgrade Agentic Workflows

on:
  schedule:
    - cron: "0 15 * * 2" # Tuesdays
  workflow_dispatch:

permissions:
  contents: read

jobs:
  upgrade:
    uses: joshjohanning/reusable-workflows/.github/workflows/gh-aw-upgrade.yml@main
    with:
      app-client-id: ${{ vars.APP_CLIENT_ID }}
    secrets:
      app-private-key: ${{ secrets.APP_PRIVATE_KEY }}
```

The `@main` reference follows central fixes. Pin it to a reviewed commit SHA if
you prefer immutable automation; gh-aw itself still defaults to `latest`.

### Inputs

| Name | Default | Description |
| --- | --- | --- |
| `gh-aw-version` | `latest` | Stable gh-aw version, e.g. `v1.2.2`. |
| `approve` | `false` | Accept safe-update manifest changes. |
| `pin-actions-to-sha` | `false` | Use SHA action-mode compilation. |
| `base-branch` | default branch | Branch to upgrade and target with the PR. |
| `app-client-id` | | GitHub App client ID. |

`approve` passes `--approve` to `gh aw upgrade`; leave it off unless you want to
approve safe-update manifest changes. `pin-actions-to-sha` recompiles with
`--action-mode action --action-tag <setup-cli SHA>` for repositories whose lock
files and validation commands use that mode.

### Secrets

| Name | Description |
| --- | --- |
| `app-private-key` | GitHub App key; pair with `app-client-id`. |
| `token` | PAT, used when no App is provided. |

### Outputs

| Name | Description |
| --- | --- |
| `pull-request-url` | URL of the opened upgrade PR, if any. |

### Local checks

Run `python3 -m unittest discover -s tests -v` and
`actionlint .github/workflows/gh-aw-upgrade.yml`.
