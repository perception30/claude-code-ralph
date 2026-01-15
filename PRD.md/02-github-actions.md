# Phase 2: GitHub Actions Release Workflow

## Objective

Create a GitHub Actions workflow that automatically builds and publishes the package to PyPI on every push to main, with version change detection to prevent duplicate releases.

## User Story Context

As a maintainer, I want pushes to main to automatically publish a new release to PyPI so that users always have access to the latest version.

## Tasks

- [x] TASK-201: Create GitHub Actions Release Workflow
  - Priority: High
  - Dependencies: TASK-102
  - Description:
    Create `.github/workflows/release.yml` with the following structure:

    ```yaml
    name: Release to PyPI

    on:
      push:
        branches: [main]

    jobs:
      check-version:
        runs-on: ubuntu-latest
        outputs:
          should_release: ${{ steps.check.outputs.should_release }}
          version: ${{ steps.check.outputs.version }}
        steps:
          - uses: actions/checkout@v4
          - name: Get current version
            id: current
            run: |
              VERSION=$(grep -Po '(?<=^version = ")[^"]*' pyproject.toml)
              echo "version=$VERSION" >> $GITHUB_OUTPUT
          - name: Check if version exists on PyPI
            id: check
            run: |
              VERSION="${{ steps.current.outputs.version }}"
              if curl -s "https://pypi.org/pypi/ralph-agent/$VERSION/json" | grep -q '"version"'; then
                echo "Version $VERSION already exists on PyPI"
                echo "should_release=false" >> $GITHUB_OUTPUT
              else
                echo "Version $VERSION not found on PyPI, will release"
                echo "should_release=true" >> $GITHUB_OUTPUT
              fi
              echo "version=$VERSION" >> $GITHUB_OUTPUT

      release:
        needs: check-version
        if: needs.check-version.outputs.should_release == 'true'
        runs-on: ubuntu-latest
        environment: pypi
        permissions:
          id-token: write  # Required for OIDC
          contents: read
        steps:
          - uses: actions/checkout@v4
          - name: Set up Python
            uses: actions/setup-python@v5
            with:
              python-version: '3.11'
          - name: Install build dependencies
            run: pip install build
          - name: Build package
            run: python -m build
          - name: Publish to PyPI
            uses: pypa/gh-action-pypi-publish@release/v1
    ```

- [ ] TASK-202: Create GitHub Environment for PyPI
  - Priority: Medium
  - Dependencies: none
  - Description:
    1. Go to repository Settings > Environments
    2. Create new environment named `pypi`
    3. Optionally add protection rules (require reviewers, wait timer)
    4. This environment name must match what's configured in PyPI Trusted Publisher

- [ ] TASK-203: Test the Release Pipeline
  - Priority: High
  - Dependencies: TASK-201, TASK-202, TASK-102
  - Description:
    1. Bump version in both `pyproject.toml` and `ralph/__init__.py` to a new version (e.g., `1.0.1`)
    2. Commit and push to main
    3. Monitor the GitHub Actions workflow
    4. Verify package appears on PyPI at https://pypi.org/project/ralph-agent/
    5. Test installation: `pip install ralph-agent`

## Verification

1. GitHub Actions workflow exists at `.github/workflows/release.yml`
2. Pushing to main with a new version triggers a successful release
3. Pushing to main without a version change skips the release (no duplicate uploads)
4. Package is installable from PyPI: `pip install ralph-agent`
