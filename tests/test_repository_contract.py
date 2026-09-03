"""Repository structure contracts for the Agent Research Workspace."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import yaml

from scripts import lab

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_METHODS = {
    "fastwam",
    "lerobot",
    "lerobot-xense",
    "tacwam",
    "xense-openpi",
}


def test_registry_gitmodules_and_focus_agree() -> None:
    result = subprocess.run(
        [
            "git",
            "config",
            "-f",
            str(ROOT / ".gitmodules"),
            "--get-regexp",
            r"^submodule\..*\.path$",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    submodules = {
        line.split(maxsplit=1)[1].removeprefix("methods/")
        for line in result.stdout.splitlines()
    }
    focus = yaml.safe_load((ROOT / "focus.yaml").read_text(encoding="utf-8"))

    assert set(lab._METHODS) == EXPECTED_METHODS
    assert submodules == EXPECTED_METHODS
    assert focus == {"default": "all", "profiles": {"all": ["*"]}}


def test_docs_have_one_directory_per_current_area() -> None:
    docs_root = ROOT / "docs"
    areas = {path.name for path in docs_root.iterdir() if path.is_dir()}

    assert areas == {"workspace", *EXPECTED_METHODS}
    assert {path.name for path in docs_root.iterdir() if path.is_file()} == {"AGENTS.md"}
    for area in areas:
        assert {"log.md", "overview.md", "plan.md"} <= {
            path.name for path in (docs_root / area).iterdir() if path.is_file()
        }


def test_agent_rules_have_one_authoritative_source() -> None:
    rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    required_rules = {
        "Do not add unrequested features, abstractions, dependencies, refactors, or cleanup.",
        "Do not ask the user to run checks the agent can run.",
    }
    required_skills = {
        "add-method",
        "context7-cli",
        "explain-diff-html",
        "find-docs",
        "gh-cli",
        "git-commit",
        "init-repo-agents",
        "karpathy-guidelines",
        "modern-python",
        "neat-freak",
        "run-experiment",
        "skill-creator",
        "summarize-experiment",
    }

    assert (ROOT / "CLAUDE.md").read_text(encoding="utf-8") == "@AGENTS.md\n"
    assert rules.startswith("# Agent Research Workspace · Agent Rules")
    assert all(rule in rules for rule in required_rules)
    assert all(f"`{skill}`" in rules for skill in required_skills)


def test_project_metadata_uses_agent_workspace_identity() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project["name"] == "agent-workspace"
