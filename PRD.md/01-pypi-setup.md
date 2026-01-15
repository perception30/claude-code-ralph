# Phase 1: PyPI Account & Trusted Publisher Setup

## Objective

Set up PyPI account and configure Trusted Publisher authentication to enable secure, keyless publishing from GitHub Actions.

## User Story Context

As a maintainer, I want to register my package on PyPI with Trusted Publisher so that GitHub Actions can publish securely without managing API tokens.

## Tasks

- [x] TASK-101: Create PyPI Account and Register Package
  - Priority: High
  - Dependencies: none
  - Description:
    1. Go to https://pypi.org/account/register/ and create an account
    2. Verify email address
    3. Enable 2FA for account security (required for Trusted Publisher)
    4. Navigate to "Your projects" > "Publishing" to prepare for Trusted Publisher setup

- [x] TASK-102: Configure Trusted Publisher on PyPI
  - Priority: High
  - Dependencies: TASK-101
  - Description:
    1. On PyPI, go to https://pypi.org/manage/account/publishing/
    2. Under "Add a new pending publisher", enter:
       - PyPI Project Name: `ralph-agent`
       - Owner: `perception30`
       - Repository name: `claude-code-ralph`
       - Workflow name: `release.yml`
       - Environment name: `pypi` (optional but recommended)
    3. Click "Add"
    4. This allows the first publish to happen without pre-registering the package

- [x] TASK-103: Update Project URLs in pyproject.toml
  - Priority: Medium
  - Dependencies: none
  - Description:
    Update the placeholder URLs in pyproject.toml to point to the actual repository:
    ```toml
    [project.urls]
    Homepage = "https://github.com/perception30/claude-code-ralph"
    Documentation = "https://github.com/perception30/claude-code-ralph#readme"
    Repository = "https://github.com/perception30/claude-code-ralph"
    Issues = "https://github.com/perception30/claude-code-ralph/issues"
    ```

## Verification

1. PyPI account is created with 2FA enabled
2. Trusted Publisher is configured for `ralph-agent` with workflow `release.yml`
3. pyproject.toml URLs point to the correct repository
