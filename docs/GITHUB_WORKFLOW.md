# GitHub collaboration workflow

## Rules

- Do **not** push directly to `main`.
- All work lands on feature branches and merges through pull requests.
- At least one teammate must review before merge.
- Never commit `.env`, API keys, tokens, or real personal/business SSNs/EINs.

## Branch naming

| Prefix | Use |
|--------|-----|
| `docs/` | Documentation and architecture PRs |
| `feature/` | New product capability |
| `fix/` | Bug or infra fix |
| `ui/` | Frontend-only work |
| `chore/` | Tooling, ignore files, scripts |

Examples:

- `docs/team-implementation-plan`
- `feature/agent-memory`
- `feature/money-pipeline`
- `ui/business-onboarding`
- `feature/daytona-mock-portal`

## Recommended branch protection for `main`

Repo admin should enable in GitHub → Settings → Branches → Branch protection rules:

1. Require a pull request before merging
2. Require at least 1 approving review
3. Dismiss stale reviews when new commits are pushed
4. Require conversation resolution before merging
5. Do not allow force pushes
6. Do not allow deletions

If the repo admin cannot enable rules immediately, treat them as team policy anyway.

## PR checklist

- [ ] Branch is not `main`
- [ ] No secrets in the diff
- [ ] README / docs updated if behavior changed
- [ ] Demo language still distinguishes estimates from confirmed money
- [ ] One teammate approved
