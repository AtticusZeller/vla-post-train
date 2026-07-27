"""FlowDAgger command launcher."""

from scripts.config import ExperimentConfig
from scripts.launchers import LaunchSpec, _argv


def build(config: ExperimentConfig) -> LaunchSpec:
    """Construct the native FlowDAgger training argv."""

    return LaunchSpec(
        argv=("python", "train_flowdagger.py", *_argv(config.native.get("argv", []))),
        cwd=config.repository_path / "flowdagger_pi05",
    )
