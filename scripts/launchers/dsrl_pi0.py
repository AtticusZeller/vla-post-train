"""DSRL π0 command launcher."""

from scripts.config import ExperimentConfig
from scripts.launchers import LaunchSpec, _argv


def build(config: ExperimentConfig) -> LaunchSpec:
    """Construct the verified module-based DSRL training argv."""

    return LaunchSpec(
        argv=("python", "-m", "examples.launch_train_sim", *_argv(config.native.get("argv", []))),
        cwd=config.repository_path,
    )
