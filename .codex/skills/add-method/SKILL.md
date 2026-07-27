---
name: add-method
description: Onboard a method, framework, benchmark, backbone, or reproduction repository into this VLA post-training workspace. Use when adding or replacing a methods/* Git submodule, connecting an official upstream to a user-controlled fork, or registering a repository for future experiments.
---

# Add Method

## Workflow

1. Read root `AGENTS.md`, `README.md`, `docs/architecture.md`, `.gitmodules`,
   and the method metadata in `scripts/lab.py`. Inspect the repository and its
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
   pointer or an existing symlink. Never install the root managed Agent block
   inside a submodule.
6. Register the path, expected branch, and official upstream in
   `scripts/lab.py`; update the README role as `method`, `framework`,
   `benchmark`, `backbone`, or `reproduction`.
7. For framework-only onboarding, stop before creating `experiments/<slug>`,
   launchers, configs, or runbooks. Create them only when a concrete experiment
   or historical migration is requested.
8. Name future framework-backed config files
   `<framework>_<policy>_<benchmark>_<task>_<variant>_seed<n>.yaml`; use the same
   components with hyphens for the YAML `id`.
9. Refresh the root Agent module index with the repository updater. Validate the
   root Agent scaffold, this Skill, CLI method status, and recursive submodules.
10. Commit and push the method revision before committing the parent gitlink.
    Report the pinned revision, branch, remotes, role, and whether experiment
    scaffolding was intentionally omitted.
