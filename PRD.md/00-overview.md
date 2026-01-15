# Automated PyPI Release Pipeline

## Overview

Implement an automated release pipeline that publishes the `ralph-agent` package to PyPI whenever changes are pushed to the main branch. The pipeline will use GitHub Actions with PyPI Trusted Publisher (OIDC) authentication for secure, keyless publishing.

### Goals
- Automate package publishing to PyPI on every push to main
- Use secure OIDC authentication (no API tokens to manage)
- Detect version changes to prevent duplicate release attempts
- Provide clear feedback on release status via GitHub Actions

### Scope
- PyPI account and package registration
- GitHub Actions workflow for building and publishing
- Version change detection logic
- Project metadata updates (URLs)

### Out of Scope
- Changelog generation
- Automated version bumping
- Test pipeline (assumed to exist or be added separately)

## User Stories

| Phase | User Story |
|-------|-----------|
| Phase 1 | As a maintainer, I want to register my package on PyPI with Trusted Publisher so that GitHub Actions can publish securely without managing API tokens. |
| Phase 2 | As a maintainer, I want pushes to main to automatically publish a new release to PyPI so that users always have access to the latest version. |

## Phase Summary

| Phase | Name | Status |
|-------|------|--------|
| 1 | PyPI Account & Trusted Publisher Setup | Complete |
| 2 | GitHub Actions Release Workflow | In Progress |
