# reusable-workflows

Reusable GitHub Actions workflows.

## Upgrade Agentic Workflows

[`.github/workflows/gh-aw-upgrade.yml`](.github/workflows/gh-aw-upgrade.yml) keeps [GitHub Agentic Workflows (gh-aw)](https://github.com/github/gh-aw) up to date in the calling repository. It:

1. Resolves the target gh-aw version (latest stable release by default).
2. Skips if every `.github/workflows/*.lock.yml` is already compiled with that version, or an upgrade PR for it is already open.
3. Runs `gh aw upgrade` (codemods, action pins, agent and skill files, and recompiled lock files).
4. Updates any other `github/gh-aw-actions/setup-cli` pins (SHA, `# vX.Y.Z` comment, `version:` input, and matching `--action-tag` SHAs) in non-lock workflow files.
5. Opens a PR from `gh-aw-upgrade/<version>` titled `chore: upgrade agentic workflows to gh-aw <version>` and closes older `gh-aw-upgrade/*` PRs it supersedes. It never merges.

### Credentials

`GITHUB_TOKEN` cannot push changes to workflow files, so provide one of the following:

- **GitHub App** (recommended): pass the `app-client-id` input and the `app-private-key` secret. The App must be installed on the repository with **Contents**, **Pull requests**, and **Workflows** read and write permissions.
- **PAT**: pass the `token` secret, with the same permissions.

PRs opened with an App or PAT token trigger the repository's normal PR checks.

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

### Inputs

| Name | Default | Description |
| --- | --- | --- |
| `gh-aw-version` | `latest` | gh-aw version to upgrade to (for example `v1.2.2`), or `latest` for the latest stable release. |
| `approve` | `false` | Pass `--approve` to `gh aw upgrade` to accept safe-update manifest changes. |
| `pin-actions-to-sha` | `false` | Recompile with `--action-mode action --action-tag <setup-cli SHA>`, for repositories whose lock files are compiled that way. |
| `base-branch` | default branch | Branch to upgrade and target with the PR. |
| `app-client-id` | | GitHub App client ID. Use with the `app-private-key` secret. |

### Secrets

| Name | Description |
| --- | --- |
| `app-private-key` | GitHub App private key. Use with the `app-client-id` input. |
| `token` | PAT with Contents, Pull requests, and Workflows write access, used when no App is provided. |

### Outputs

| Name | Description |
| --- | --- |
| `pull-request-url` | URL of the opened upgrade PR, if any. |
