"""Safe declarative command launcher."""

from scripts.config import ConfigError, ExperimentConfig
from scripts.launchers import LaunchSpec, _argv


def build(config: ExperimentConfig) -> LaunchSpec:
    """Build an argv-only command without invoking a shell string."""

    native = config.native
    command = native.get("command")
    if isinstance(command, str):
        raise ConfigError("native.command must be an argv list, not a shell string")
    argv = _argv(command, "native.command")
    if not argv:
        raise ConfigError("native.command cannot be empty")
    return LaunchSpec(argv=tuple(argv), cwd=config.repository_path)
