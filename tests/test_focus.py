"""Focus profile resolution and switch-planning tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import focus, lab
from scripts.config import ConfigError

_KNOWN = ("alpha", "beta", "gamma")


def _write_focus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, document: dict) -> Path:
    path = tmp_path / "focus.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(focus, "FOCUS_FILE", path)
    return path


def test_committed_profiles_resolve_against_the_registry() -> None:
    """The repository's own focus.yaml must stay in sync with _METHODS."""

    for name in focus.profile_names():
        resolved, members = focus.load_profile(name, lab._METHODS)
        assert resolved == name
        assert members <= set(lab._METHODS)
    _, everything = focus.load_profile("all", lab._METHODS)
    assert everything == set(lab._METHODS)


def test_star_expands_to_every_known_method(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_focus(tmp_path, monkeypatch, {"default": "all", "profiles": {"all": ["*"]}})
    assert focus.load_profile("all", _KNOWN) == ("all", set(_KNOWN))


def test_omitted_name_falls_back_to_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_focus(
        tmp_path,
        monkeypatch,
        {"default": "small", "profiles": {"all": ["*"], "small": ["alpha"]}},
    )
    assert focus.load_profile(None, _KNOWN) == ("small", {"alpha"})


def test_unknown_profile_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_focus(tmp_path, monkeypatch, {"default": "all", "profiles": {"all": ["*"]}})
    with pytest.raises(ConfigError, match="unknown focus profile"):
        focus.load_profile("nope", _KNOWN)


def test_unregistered_method_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_focus(
        tmp_path,
        monkeypatch,
        {"default": "small", "profiles": {"small": ["alpha", "delta"]}},
    )
    with pytest.raises(ConfigError, match="delta"):
        focus.load_profile("small", _KNOWN)


def test_missing_active_key_means_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Git treats an unset submodule.<name>.active as active; so must we."""

    monkeypatch.setattr(
        focus,
        "_git",
        lambda *_args: (0, "submodule.methods/beta.active false"),
    )
    assert focus.active_methods(_KNOWN) == {"alpha", "gamma"}


def test_active_pathspec_selects_the_listed_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    """submodule.active is the flag that survives `submodule update --init`."""

    monkeypatch.setattr(
        focus,
        "_git",
        lambda *_args: (
            0,
            "submodule.methods/alpha.url git@example.com:alpha.git\n"
            "submodule.active methods/alpha\n"
            "submodule.active methods/gamma",
        ),
    )
    assert focus.active_methods(_KNOWN) == {"alpha", "gamma"}


def test_per_submodule_key_overrides_the_pathspec(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        focus,
        "_git",
        lambda *_args: (
            0,
            "submodule.active methods/alpha\n"
            "submodule.active methods/gamma\n"
            "submodule.methods/gamma.active false",
        ),
    )
    assert focus.active_methods(_KNOWN) == {"alpha"}


def test_active_methods_survives_an_empty_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(focus, "_git", lambda *_args: (1, ""))
    assert focus.active_methods(_KNOWN) == set(_KNOWN)


def test_current_profile_is_custom_without_a_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_focus(
        tmp_path,
        monkeypatch,
        {"default": "all", "profiles": {"all": ["*"], "small": ["alpha"]}},
    )
    monkeypatch.setattr(focus, "active_methods", lambda _known: {"alpha", "beta"})
    assert focus.current_profile(_KNOWN) == "custom"
    monkeypatch.setattr(focus, "active_methods", lambda _known: {"alpha"})
    assert focus.current_profile(_KNOWN) == "small"


def _stub_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan a real switch without touching any worktree."""

    selected = set(lab._METHODS)
    selected.remove(next(iter(selected)))
    monkeypatch.setattr(lab.focus, "load_profile", lambda _profile, _known: ("small", selected))
    monkeypatch.setattr(lab.focus, "active_methods", lambda _known: set(lab._METHODS))
    monkeypatch.setattr(lab.focus, "is_populated", lambda _method: True)
    monkeypatch.setattr(
        lab.focus,
        "deletion_manifest",
        lambda methods: [
            focus.Removal(method=method, path=Path(method), size_bytes=1024) for method in methods
        ],
    )
    for name in ("drop_worktree", "restore_worktree"):
        monkeypatch.setattr(
            lab.focus,
            name,
            lambda _method: pytest.fail("focus must not mutate the worktree here"),
        )
    monkeypatch.setattr(
        lab.focus,
        "set_active",
        lambda _selected, _known: pytest.fail("focus must not rewrite config here"),
    )


def test_dry_run_plans_without_mutating(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stub_switch(monkeypatch)
    assert lab._method_focus("small", dry_run=True, assume_yes=False) == 0
    assert "dry-run" in capsys.readouterr().out


def test_deletion_requires_explicit_consent_without_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_switch(monkeypatch)
    monkeypatch.setattr(lab.sys.stdin, "isatty", lambda: False)
    with pytest.raises(ConfigError, match="--yes"):
        lab._method_focus("small", dry_run=False, assume_yes=False)


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "protocol.file.allow=always", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def parent_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway superproject with one `methods/child` submodule."""

    child = tmp_path / "child"
    child.mkdir()
    _git(child, "init", "-q")
    (child / "file.txt").write_text("child\n", encoding="utf-8")
    _git(child, "add", "-A")
    _git(child, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")

    parent = tmp_path / "parent"
    parent.mkdir()
    _git(parent, "init", "-q")
    _git(parent, "submodule", "add", "-q", str(child), "methods/child")
    _git(parent, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")

    monkeypatch.setattr(focus, "ROOT", parent)
    return parent


def test_dropping_a_worktree_removes_its_directory_and_stays_reversible(
    parent_repo: Path,
) -> None:
    """A deinit alone leaves an empty directory; the skip-worktree bit hides its removal."""

    assert focus.is_populated("child")

    focus.drop_worktree("child")
    assert not (parent_repo / "methods" / "child").exists()
    assert _git(parent_repo, "status", "--porcelain") == ""

    focus.restore_worktree("child")
    assert focus.is_populated("child")
    assert _git(parent_repo, "status", "--porcelain") == ""
