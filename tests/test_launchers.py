"""Method launcher argv tests."""

from scripts.config import ROOT, load_config
from scripts.launchers import build_launch_spec


def test_flowdagger_argv_is_exact() -> None:
    config = load_config("experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml")
    spec = build_launch_spec(config)
    assert spec.cwd == ROOT / "methods/flowdagger/flowdagger_pi05"
    assert spec.argv == (
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "dsrl_pi0",
        "python",
        "train_flowdagger.py",
        *config.native["argv"],
    )


def test_dsrl_argv_is_exact() -> None:
    config = load_config("experiments/dsrl-pi0/configs/libero90_task57_smoke_seed0.yaml")
    spec = build_launch_spec(config)
    assert spec.cwd == ROOT / "methods/dsrl-pi0"
    assert spec.argv == (
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "dsrl_pi0",
        "python",
        "-m",
        "examples.launch_train_sim",
        *config.native["argv"],
    )


def test_rlinf_argv_is_exact() -> None:
    config = load_config("experiments/rlinf/configs/libero10_task0_medium_seed0.yaml")
    spec = build_launch_spec(config)
    assert spec.cwd == ROOT / "methods/rlinf"
    assert spec.argv == (
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "dsrl_pi0",
        "bash",
        "examples/offline_rl/run_libero10_task0_comparison.sh",
        "medium",
    )


def test_rlinf_rlt_stage2_argv_is_exact() -> None:
    config = load_config("experiments/rlinf/configs/rlt_maniskill_stage2_12h_seed2026.yaml")
    spec = build_launch_spec(config)
    assert spec.cwd == ROOT / "methods/rlinf"
    assert spec.argv == (
        "bash",
        "experiments/rlt-maniskill/launch.sh",
        "stage2-12h",
    )
    assert dict(spec.environment) == {
        "RLINF_VENV": "/root/RLinf/.venv",
        "UV_PROJECT_ENVIRONMENT": "/root/RLinf/.venv",
        "UV_NO_SYNC": "1",
    }
