"""RLinf native experiment command launcher."""

from scripts.config import ExperimentConfig
from scripts.launchers import LaunchSpec, _argv


def build(config: ExperimentConfig) -> LaunchSpec:
    """Construct the native RLinf experiment-script argv."""

    script = str(
        config.native.get("script", "examples/offline_rl/run_libero10_task0_comparison.sh")
    )
    return LaunchSpec(
        argv=("bash", script, *_argv(config.native.get("argv", []))),
        cwd=config.repository_path,
    )
