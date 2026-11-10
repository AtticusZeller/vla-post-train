---
name: add-method
description: Onboard a method, framework, benchmark, backbone, or reproduction repository into the Agent Research Workspace. Use when adding or replacing a methods/* Git submodule, connecting an official upstream to a user-controlled fork, or registering a repository for future experiments.
---

# Add Method

## Workflow

1. Read root `AGENTS.md`, `README.md`, `docs/AGENTS.md`, `docs/workspace/overview.md`, and `.gitmodules`.
   Inspect the repository and its
   existing Agent files before changing anything.
2. Use authenticated `gh` and Git reads to identify the official repository,
   default branch, user fork, current branches, nested submodules, and license.
   Require a clean checkout.
3. Use the user fork as `origin` and the official repository as `upstream`.
   Preserve divergent or historical branches. If no clean integration branch
   exists, create `workspace` from the current upstream default revision; never
   reset or force-push an existing branch.
4. Add the fork through an HTTPS submodule URL at `methods/<slug>`, set the
   selected branch in `.gitmodules`, and pin an exact remotely available commit.
   Configure the local submodule's `upstream` remote.
5. Keep method Agent guidance method-specific. Preserve a useful upstream
   `AGENTS.md` or write a concise repository guide; use a short `CLAUDE.md`
   pointer or an existing symlink. Never copy the root workspace rules into a
   submodule.
6. Add a README row with the role `method`, `framework`, `benchmark`, `backbone`, or
   `reproduction`. Create
   `docs/<slug>/{plan,log,overview,cmd}.md` under the `docs/AGENTS.md` contract.
7. Keep onboarding to the submodule, README row, and `docs/<slug>/`. Experiment
   configs and runbooks belong to the method repository, created only when a
   concrete experiment is requested.
8. Validate the docs structure, this Skill, `git submodule status`, that
   `.gitmodules` and the README table agree, and recursive submodules.
9. Commit and push the method revision before committing the parent gitlink.
    Report the pinned revision, branch, remotes, role, and whether the nested
    submodules were left uninitialized.
